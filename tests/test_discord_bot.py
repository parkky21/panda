import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, ANY
import discord

# Ensure environment variables are mocked before imports
@pytest.fixture(autouse=True)
def setup_mock_env(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "mock_bedrock_token")
    monkeypatch.setenv("MODEL_ID", "mock-model")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_discord_token")

import discord_bot

def test_split_response():
    # Test short response
    short_text = "Hello World"
    chunks = discord_bot.split_response(short_text)
    assert chunks == [short_text]

    # Test exact limit split
    exact_text = "A" * 10
    chunks = discord_bot.split_response(exact_text, chunk_size=10)
    assert chunks == [exact_text]

    # Test split by space/newline
    long_text = "Line 1\nLine 2\nLine 3"
    chunks = discord_bot.split_response(long_text, chunk_size=10)
    assert len(chunks) == 3
    assert chunks[0] == "Line 1"
    assert chunks[1] == "Line 2"
    assert chunks[2] == "Line 3"

@pytest.mark.anyio
async def test_send_response():
    mock_message = MagicMock()
    mock_message.reply = AsyncMock()
    
    text = "Hello\nWorld"
    await discord_bot.send_response(mock_message, text)
    mock_message.reply.assert_called_once_with(text)

@pytest.mark.anyio
async def test_cron_loop_async():
    mock_orchestrator = MagicMock()
    mock_orchestrator.scheduler.run_due_tasks = MagicMock()
    
    # Run cron loop but patch asyncio.sleep to break early
    with patch('asyncio.sleep', SideEffect=AsyncMock()) as mock_sleep:
        # We want to raise GeneratorExit or just cancel to stop the infinite loop after 1 run
        mock_sleep.side_effect = asyncio.CancelledError()
        
        with pytest.raises(asyncio.CancelledError):
            await discord_bot.cron_loop_async(mock_orchestrator)
            
        mock_orchestrator.scheduler.run_due_tasks.assert_called_once_with(mock_orchestrator.skills_manager, ANY)

@pytest.mark.anyio
async def test_commands():
    # Setup mock ctx
    mock_ctx = MagicMock()
    mock_ctx.channel.id = 999
    mock_ctx.send = AsyncMock()
    
    # 1. Test start command
    await discord_bot.start_cmd(mock_ctx)
    assert discord_bot.chat_histories[999] == []
    mock_ctx.send.assert_called_once()
    assert "Panda's Bamboo Corner" in mock_ctx.send.call_args[0][0]

    # 2. Test reset command
    mock_ctx.send.reset_mock()
    discord_bot.chat_histories[999] = [{"role": "user", "content": [{"text": "hi"}]}]
    await discord_bot.reset_cmd(mock_ctx)
    assert discord_bot.chat_histories[999] == []
    mock_ctx.send.assert_called_once_with("🐼 Conversation history cleared!")

    # 3. Test reflect command empty history
    mock_ctx.send.reset_mock()
    await discord_bot.reflect_cmd(mock_ctx)
    mock_ctx.send.assert_called_once_with("🐼 Nothing to reflect on yet! Let's chat first.")

    # 4. Test reflect command with history
    mock_ctx.send.reset_mock()
    discord_bot.chat_histories[999] = [{"role": "user", "content": [{"text": "some info"}]}]
    mock_orchestrator = MagicMock()
    mock_orchestrator.reflect_and_improve = MagicMock(return_value="Reflection report")
    discord_bot.orchestrator = mock_orchestrator
    
    await discord_bot.reflect_cmd(mock_ctx)
    assert mock_ctx.send.call_count == 2
    mock_ctx.send.assert_any_call("🐼 Reflecting on our conversation...")
    mock_ctx.send.assert_any_call("✓ Reflection report")

@pytest.mark.anyio
@patch('discord_bot.bot')
async def test_on_message_events(mock_bot):
    # 1. Ignore self messages
    mock_bot.user = MagicMock()
    mock_bot.process_commands = AsyncMock()
    mock_message = MagicMock()
    mock_message.author = mock_bot.user
    
    await discord_bot.on_message(mock_message)
    mock_bot.process_commands.assert_not_called()

    # 2. Process commands starting with !
    mock_message.author = MagicMock() # not bot
    mock_message.content = "!reflect"
    
    await discord_bot.on_message(mock_message)
    mock_bot.process_commands.assert_called_once_with(mock_message)

    # 3. Handle non-command message not in DM and not mentioned
    mock_bot.process_commands.reset_mock()
    mock_message.content = "hello panda"
    mock_message.guild = MagicMock() # not DM
    mock_message.mentions = [] # not mentioned
    
    with patch('discord_bot.handle_conversation', AsyncMock()) as mock_handle:
        await discord_bot.on_message(mock_message)
        mock_handle.assert_not_called()

    # 4. Handle DM message
    mock_message.guild = None # DM
    with patch('discord_bot.handle_conversation', AsyncMock()) as mock_handle:
        await discord_bot.on_message(mock_message)
        mock_handle.assert_called_once_with(mock_message, "hello panda")

    # 5. Handle mention message
    mock_message.guild = MagicMock() # not DM
    mock_message.mentions = [mock_bot.user]
    mock_bot.user.id = 12345
    mock_message.content = "<@12345> hello there"
    
    with patch('discord_bot.handle_conversation', AsyncMock()) as mock_handle:
        await discord_bot.on_message(mock_message)
        mock_handle.assert_called_once_with(mock_message, "hello there")

@pytest.mark.anyio
@patch('asyncio.to_thread')
@patch('discord_bot.send_response', AsyncMock())
async def test_handle_conversation(mock_to_thread):
    mock_orchestrator = MagicMock()
    mock_orchestrator.chat.return_value = {
        "content": [{"text": "Hello user"}]
    }
    discord_bot.orchestrator = mock_orchestrator
    mock_to_thread.return_value = mock_orchestrator.chat.return_value

    mock_message = MagicMock()
    mock_message.channel.id = 888
    mock_message.reply = AsyncMock()
    mock_message.channel.send = AsyncMock()
    mock_message.channel.typing.return_value.__aenter__ = AsyncMock()
    mock_message.channel.typing.return_value.__aexit__ = AsyncMock()

    await discord_bot.handle_conversation(mock_message, "User greeting")

    # Verify history was appended
    assert len(discord_bot.chat_histories[888]) == 1
    assert discord_bot.chat_histories[888][0]["content"][0]["text"] == "User greeting"

    # Verify orchestrator was run
    mock_to_thread.assert_called_once()
    
    # Test callback invocation
    callbacks = mock_to_thread.call_args[0]
    on_tool_start = callbacks[2]
    on_tool_end = callbacks[3]

    # Verify we can execute callbacks without throwing
    on_tool_start("write_memory", {"content": "fact"})
    on_tool_end("write_memory", "Success")

    # Let the event loop run callbacks scheduled thread-safely
    await asyncio.sleep(0.1)
    
    # Verify typing was called and reply was sent
    mock_message.channel.typing.assert_called_once()

@pytest.mark.anyio
async def test_setup_hook():
    mock_bot_instance = discord_bot.PandaBot(command_prefix="!", intents=discord.Intents.default())
    mock_bot_instance.loop = MagicMock()
    
    coros = []
    def mock_create_task(coro):
        coros.append(coro)
        return MagicMock()
    mock_bot_instance.loop.create_task = mock_create_task
    
    await mock_bot_instance.setup_hook()
    assert len(coros) == 1
    
    for coro in coros:
        coro.close()

def test_main_missing_token(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    with pytest.raises(SystemExit) as excinfo:
        discord_bot.main()
    assert excinfo.value.code == 1

@patch('discord_bot.bot')
@patch('discord_bot.PandaOrchestrator')
def test_main_with_token(mock_orchestrator, mock_bot, monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_token")
    discord_bot.main()
    mock_bot.run.assert_called_once_with("mock_token")


@pytest.mark.anyio
@patch('discord_bot.notify_user')
async def test_cron_loop_email_reply_auto_stop(mock_notify):
    mock_orchestrator = MagicMock()
    
    # Setup the scheduled task mapping
    mock_orchestrator.scheduler.tasks = {
        "check_reply_task": {
            "interval_seconds": 10,
            "command": "run_skill check_emails parth.kale.dev@gmail.com",
            "last_run": 0
        }
    }
    mock_orchestrator.scheduler.unschedule_task = MagicMock()
    
    # We want to capture the on_task_run callback passed to run_due_tasks
    def mock_run_due_tasks(skills_manager, on_task_run):
        output = (
            "📩 **Found 1 new unread email(s).**\n"
            "👤 **From:** parth.kale.dev@gmail.com\n"
            "✉️ **Subject:** Meeting Request\n"
            "📝 **Body:** Let's meet at 3 PM\n"
        )
        on_task_run("check_reply_task", "success", output)
        
    mock_orchestrator.scheduler.run_due_tasks.side_effect = mock_run_due_tasks
    
    with patch('asyncio.sleep', AsyncMock(side_effect=asyncio.CancelledError())):
        with pytest.raises(asyncio.CancelledError):
            await discord_bot.cron_loop_async(mock_orchestrator)
            
    # Verify unschedule_task was called because we had a filter and found 1 new unread
    mock_orchestrator.scheduler.unschedule_task.assert_called_once_with("check_reply_task")
    mock_notify.assert_not_called()


@pytest.mark.anyio
@patch('discord_bot.notify_user')
async def test_cron_loop_email_reply_unfiltered_auto_stop(mock_notify):
    mock_orchestrator = MagicMock()
    
    # Setup scheduled task mapping without sender filter
    mock_orchestrator.scheduler.tasks = {
        "unfiltered_task": {
            "interval_seconds": 10,
            "command": "run_skill check_emails",
            "last_run": 0
        }
    }
    mock_orchestrator.scheduler.unschedule_task = MagicMock()
    
    # Scenario A: Non-reply email output -> should NOT stop
    def mock_run_due_tasks_no_stop(skills_manager, on_task_run):
        output = (
            "📩 **Found 5 new unread email(s). Showing the latest 5:**\n"
            "👤 **From:** Instamart <noreply@swiggy.in>\n"
            "✉️ **Subject:** How else will we know, Parth?\n"
        )
        on_task_run("unfiltered_task", "success", output)
        
    mock_orchestrator.scheduler.run_due_tasks.side_effect = mock_run_due_tasks_no_stop
    
    with patch('asyncio.sleep', AsyncMock(side_effect=asyncio.CancelledError())):
        with pytest.raises(asyncio.CancelledError):
            await discord_bot.cron_loop_async(mock_orchestrator)
            
    mock_orchestrator.scheduler.unschedule_task.assert_not_called()
    mock_notify.assert_not_called()
    
    # Scenario B: Reply email output (with Re:) -> should stop
    mock_orchestrator.scheduler.unschedule_task.reset_mock()
    mock_notify.reset_mock()
    def mock_run_due_tasks_stop(skills_manager, on_task_run):
        output = (
            "📩 **Found 17451 new unread email(s). Showing the latest 5:**\n"
            "👤 **From:** Parth Kale <parth.kale.dev@gmail.com>\n"
            "✉️ **Subject:** Re: Meeting Request\n"
        )
        on_task_run("unfiltered_task", "success", output)
        
    mock_orchestrator.scheduler.run_due_tasks.side_effect = mock_run_due_tasks_stop
    
    with patch('asyncio.sleep', AsyncMock(side_effect=asyncio.CancelledError())):
        with pytest.raises(asyncio.CancelledError):
            await discord_bot.cron_loop_async(mock_orchestrator)
            
    mock_orchestrator.scheduler.unschedule_task.assert_called_once_with("unfiltered_task")
    mock_notify.assert_not_called()

