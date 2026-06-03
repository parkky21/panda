import os
import sys
import logging
import asyncio
import re
from dotenv import load_dotenv
import discord
from discord.ext import commands
from agent.orchestrator import PandaOrchestrator
from agent.config import AgentConfig

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Dictionary to store chat histories by channel_id (covers DMs and guild channels)
chat_histories = {}
orchestrator = None

def split_response(text: str, chunk_size: int = 1900) -> list[str]:
    """Splits response into chunks of up to chunk_size characters to avoid Discord's limit."""
    chunks = []
    while len(text) > chunk_size:
        split_idx = text.rfind('\n', 0, chunk_size)
        if split_idx == -1:
            split_idx = text.rfind(' ', 0, chunk_size)
        if split_idx == -1:
            split_idx = chunk_size
            
        chunks.append(text[:split_idx].strip())
        text = text[split_idx:].strip()
    if text:
        chunks.append(text)
    return chunks

async def send_response(message, text: str):
    """Helper to send text chunks to message channel."""
    chunks = split_response(text)
    for chunk in chunks:
        await message.reply(chunk)

last_active_channel = None

def notify_user(text: str):
    if last_active_channel:
        asyncio.run_coroutine_threadsafe(
            last_active_channel.send(text),
            bot.loop
        )

async def cron_loop_async(orchestrator_instance):
    """Runs background scheduler check every 10 seconds."""
    while True:
        try:
            def on_task_run(name, status, output):
                if output.strip():
                    # Check if it's an email check task
                    task_info = orchestrator_instance.scheduler.tasks.get(name)
                    is_email_task = False
                    if task_info:
                        command = task_info.get("command", "")
                        if "check_emails" in command:
                            is_email_task = True
                    
                    if is_email_task:
                        command = task_info.get("command", "")
                        parts = command.split()
                        has_sender_filter = False
                        if len(parts) > 1 and parts[0] == "run_skill" and parts[1] == "check_emails" and len(parts) > 2:
                            has_sender_filter = True
                        
                        # Parse unread count from output
                        match = re.search(r"Found (\d+) new unread", output)
                        if match:
                            num_emails = int(match.group(1))
                            if num_emails > 0:
                                should_stop = False
                                
                                # Extract email details from the first matching email in output
                                from_match = re.search(r"👤 \*\*From:\*\* (.*?)(?:\n|$)", output)
                                subject_match = re.search(r"✉️ \*\*Subject:\*\* (.*?)(?:\n|$)", output)
                                body_match = re.search(r"📝 \*\*Body:\*\* (.*?)(?:\n|$)", output)
                                
                                sender = from_match.group(1) if from_match else "Unknown"
                                subject = subject_match.group(1) if subject_match else "No Subject"
                                body = body_match.group(1) if body_match else ""
                                
                                if has_sender_filter:
                                    should_stop = True
                                else:
                                    # Without filter, check if the first email matches reply criteria
                                    has_reply_subject = bool(re.search(r"\bRe\b:", subject, re.IGNORECASE))
                                    has_dev_sender = "parth.kale.dev@gmail.com" in sender
                                    if has_reply_subject or has_dev_sender:
                                        should_stop = True
                                        
                                if should_stop:
                                    orchestrator_instance.scheduler.unschedule_task(name)
                    else:
                        # For non-email tasks, notify normally
                        notify_user(f"⏰ **Background Task '{name}' Executed:**\n{output}")
            await asyncio.to_thread(
                orchestrator_instance.scheduler.run_due_tasks,
                orchestrator_instance.skills_manager,
                on_task_run
            )
        except Exception as e:
            logger.error(f"Error in background cron loop: {e}")
        await asyncio.sleep(10)

class PandaBot(commands.Bot):
    async def setup_hook(self):
        # Start background cron loop
        self.loop.create_task(cron_loop_async(orchestrator))
        print("🐼 Background cron loop scheduled.")

intents = discord.Intents.default()
intents.message_content = True

bot = PandaBot(command_prefix="!", intents=intents)

@bot.command(name="start")
async def start_cmd(ctx):
    """Resets conversation and welcomes the user."""
    channel_id = ctx.channel.id
    chat_histories[channel_id] = []
    welcome_text = (
        "🐼 **Panda's Bamboo Corner** 🐼\n\n"
        "Hey! I'm Panda, your warm and loyal companion. Ask me anything, tell me about your day, "
        "or let me help you build your projects!\n\n"
        "Use `!reset` to clear history, or `!reflect` to trigger a self-reflection summary."
    )
    await ctx.send(welcome_text)

@bot.command(name="reset")
async def reset_cmd(ctx):
    """Resets conversation history."""
    channel_id = ctx.channel.id
    chat_histories[channel_id] = []
    await ctx.send("🐼 Conversation history cleared!")

@bot.command(name="reflect")
async def reflect_cmd(ctx):
    """Triggers self-reflection loop for the current conversation."""
    channel_id = ctx.channel.id
    history = chat_histories.get(channel_id, [])
    if not history:
        await ctx.send("🐼 Nothing to reflect on yet! Let's chat first.")
        return
    await ctx.send("🐼 Reflecting on our conversation...")
    report = await asyncio.to_thread(orchestrator.reflect_and_improve, history)
    await ctx.send(f"✓ {report}")

async def handle_conversation(message, user_text: str):
    """Processes message content with the orchestrator."""
    global last_active_channel
    last_active_channel = message.channel
    # Check for empty text (which can happen with voice notes or attachments)
    if not user_text.strip():
        if message.attachments:
            is_voice = False
            for attachment in message.attachments:
                content_type = attachment.content_type
                if content_type and content_type.startswith("audio/"):
                    is_voice = True
                elif attachment.filename.lower().endswith(('.ogg', '.mp3', '.wav', '.m4a', '.mp4')):
                    is_voice = True
            
            if is_voice:
                await message.reply("🐼 I can see you sent a voice message, but I can't listen to audio yet! Please type your message. 🎙️")
            else:
                await message.reply("🐼 I received your attachment, but I can only understand text messages right now! Please type your message. 📄")
        else:
            await message.reply("🐼 It looks like you sent an empty message! How can I help you? 🐼")
        return

    channel_id = message.channel.id
    if channel_id not in chat_histories:
        chat_histories[channel_id] = []
        
    history = chat_histories[channel_id]
    history.append({"role": "user", "content": [{"text": user_text}]})
    
    async with message.channel.typing():
        loop = asyncio.get_running_loop()
        
        # Define non-blocking callbacks for tool run indicators
        def on_tool_call_start(tool_name, tool_args):
            args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
            asyncio.run_coroutine_threadsafe(
                message.channel.send(f"🔧 **Tool Start:** `{tool_name}({args_str})`"),
                loop
            )
            
        def on_tool_call_end(tool_name, result):
            preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
            asyncio.run_coroutine_threadsafe(
                message.channel.send(f"✓ **Tool End:** `{tool_name}` finished.\nResult: `{preview}`"),
                loop
            )
            
        try:
            # Run orchestrator chat loop in a thread pool
            response = await asyncio.to_thread(
                orchestrator.chat,
                history,
                on_tool_call_start,
                on_tool_call_end
            )
            
            # Extract assistant response text
            content_blocks = response.get("content", [])
            text_response = "".join(block.get("text", "") for block in content_blocks if "text" in block)
            
            # Strip think tags to keep conversation clean
            text_response = re.sub(r"<think>.*?</think>", "", text_response, flags=re.DOTALL)
            text_response = re.sub(r"<think>.*", "", text_response, flags=re.DOTALL).strip()
            
            # Reply to user
            await send_response(message, text_response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.reply(f"⚠️ An error occurred: {e}")

@bot.event
async def on_message(message):
    """Processes incoming messages, filtering for DMs or mentions."""
    # Avoid responding to self
    if message.author == bot.user:
        return

    logger.info(f"Received message from {message.author}: '{message.content}' (Guild: {message.guild})")

    # Check if command
    if message.content.startswith('!'):
        logger.info(f"Processing command: {message.content}")
        await bot.process_commands(message)
        return

    # For non-command messages: only reply in DMs or if mentioned
    is_dm = message.guild is None
    is_mentioned = bot.user in message.mentions

    if is_dm or is_mentioned:
        logger.info(f"Handling conversation message (is_dm={is_dm}, is_mentioned={is_mentioned})")
        content = message.content
        if is_mentioned:
            content = re.sub(rf'<@!?{bot.user.id}>', '', content).strip()
        await handle_conversation(message, content)
    else:
        logger.info("Message ignored (not DM and bot not mentioned)")

def main():
    global orchestrator
    
    token = AgentConfig.get_discord_token()
    if not token:
        print("Error: DISCORD_BOT_TOKEN is not set in your .env file.", file=sys.stderr)
        print("Please create a bot application at the Discord Developer Portal and set the token.", file=sys.stderr)
        sys.exit(1)
        
    memory_dir = "./memory"
    skills_dir = "./skills"
    
    # Initialize main orchestrator
    orchestrator = PandaOrchestrator(
        memory_dir=memory_dir,
        skills_dir=skills_dir,
        notify_callback=notify_user
    )
    
    # Start bot polling
    print("🐼 Starting Panda Discord Bot Gateway...")
    bot.run(token)

if __name__ == '__main__':
    main()
