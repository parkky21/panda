import pytest
import json
from unittest.mock import MagicMock, patch
from agent.orchestrator import PandaOrchestrator

@pytest.fixture
def mock_boto():
    with patch('boto3.client') as mock:
        yield mock

def test_orchestrator_initialization(temp_memory_dir, temp_skills_dir, mock_boto):
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    
    orchestrator = PandaOrchestrator(
        memory_dir=temp_memory_dir,
        skills_dir=temp_skills_dir,
        model_id="mock-model",
        region_name="us-east-1"
    )
    
    assert orchestrator.model_id == "mock-model"
    mock_boto.assert_called_once_with("bedrock-runtime", region_name="us-east-1")
    
    # Test system prompt builder
    sys_prompt = orchestrator._build_system_prompt()
    assert "Soul" in sys_prompt
    assert "User Profile" in sys_prompt
    assert "Agent Memory" in sys_prompt

def test_orchestrator_chat_standard(temp_memory_dir, temp_skills_dir, mock_boto):
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    
    # Configure mock response for standard text (no tools)
    mock_client.converse.return_value = {
        "stopReason": "end_turn",
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "Hello, Parth!"}]
            }
        }
    }
    
    orchestrator = PandaOrchestrator(temp_memory_dir, temp_skills_dir)
    history = [{"role": "user", "content": [{"text": "Hi"}]}]
    
    res = orchestrator.chat(history)
    assert res["content"][0]["text"] == "Hello, Parth!"
    assert len(history) == 2  # user + assistant

def test_orchestrator_chat_with_tool_loop(temp_memory_dir, temp_skills_dir, mock_boto):
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    
    # Configure mock responses:
    # 1st call returns tool_use (read_user)
    # 2nd call returns standard response (end_turn)
    mock_client.converse.side_effect = [
        {
            "stopReason": "tool_use",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tool-id-1",
                                "name": "read_user",
                                "input": {}
                            }
                        }
                    ]
                }
            }
        },
        {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Finished reading profile!"}]
                }
            }
        }
    ]
    
    orchestrator = PandaOrchestrator(temp_memory_dir, temp_skills_dir)
    
    # Mock read_user in memory_manager
    orchestrator.memory_manager.read_user = MagicMock(return_value="Parth profile content")
    
    history = [{"role": "user", "content": [{"text": "Read my profile"}]}]
    
    # Setup spy callbacks
    spy_start = MagicMock()
    spy_end = MagicMock()
    
    res = orchestrator.chat(history, on_tool_call_start=spy_start, on_tool_call_end=spy_end)
    assert res["content"][0]["text"] == "Finished reading profile!"
    
    spy_start.assert_called_once_with("read_user", {})
    spy_end.assert_called_once_with("read_user", "Parth profile content")
    
    # Check history structure:
    # 1. user msg
    # 2. assistant toolUse msg
    # 3. user toolResult msg
    # 4. assistant final text msg
    assert len(history) == 4
    assert history[2]["role"] == "user"
    assert "toolResult" in history[2]["content"][0]
    assert history[2]["content"][0]["toolResult"]["content"][0]["text"] == "Parth profile content"

def test_context_compression_trigger(temp_memory_dir, temp_skills_dir, mock_boto):
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    
    # Mock responses:
    # 1st call: compression summarizer call (end_turn)
    # 2nd call: actual user query chat call (end_turn)
    mock_client.converse.side_effect = [
        {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "- Summary of conversation"}]
                }
            }
        },
        {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Pushed memory!"}]
                }
            }
        }
    ]
    
    orchestrator = PandaOrchestrator(temp_memory_dir, temp_skills_dir)
    
    # Build 14 messages (7 rounds)
    history = []
    for i in range(7):
        history.append({"role": "user", "content": [{"text": f"Msg {i}"}]})
        history.append({"role": "assistant", "content": [{"text": f"Reply {i}"}]})
        
    assert len(history) == 14
    
    # Trigger chat which will compress
    res = orchestrator.chat(history)
    assert res["content"][0]["text"] == "Pushed memory!"
    
    # Verify first 8 messages were compressed and pruned from history
    assert len(history) < 14
    assert orchestrator.conversation_summary == "- Summary of conversation"

def test_reflect_and_improve(temp_memory_dir, temp_skills_dir, mock_boto):
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    
    # Mock response for reflection Converse API call
    mock_client.converse.return_value = {
        "stopReason": "end_turn",
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "* Lesson 1\n* Lesson 2"}]
            }
        }
    }
    
    orchestrator = PandaOrchestrator(temp_memory_dir, temp_skills_dir)
    history = [
        {"role": "user", "content": [{"text": "Help me fix tests"}]},
        {"role": "assistant", "content": [{"text": "I fixed them"}]}
    ]
    
    res = orchestrator.reflect_and_improve(history)
    assert "Self-reflection complete" in res
    
    # Verify memory.md updated
    memory_content = orchestrator.memory_manager.read_memory()
    assert "SESSION REFLECTION" in memory_content
    assert "Lesson 1" in memory_content


def test_context_compression_with_tool_results(temp_memory_dir, temp_skills_dir, mock_boto):
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    
    mock_client.converse.side_effect = [
        {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "- Summary of conversation"}]
                }
            }
        },
        {
            "stopReason": "end_turn",
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "Pushed memory!"}]
                }
            }
        }
    ]
    
    orchestrator = PandaOrchestrator(temp_memory_dir, temp_skills_dir)
    
    # Build 14 messages where index 8 is a toolResult, and index 10 is a clean user message
    history = []
    # 0, 1
    history.append({"role": "user", "content": [{"text": "Msg 0"}]})
    history.append({"role": "assistant", "content": [{"text": "Reply 0"}]})
    # 2, 3
    history.append({"role": "user", "content": [{"text": "Msg 1"}]})
    history.append({"role": "assistant", "content": [{"text": "Reply 1"}]})
    # 4, 5
    history.append({"role": "user", "content": [{"text": "Msg 2"}]})
    history.append({"role": "assistant", "content": [{"text": "Reply 2"}]})
    # 6, 7 (assistant makes tool call)
    history.append({"role": "user", "content": [{"text": "Msg 3"}]})
    history.append({"role": "assistant", "content": [{"toolUse": {"toolUseId": "1", "name": "read_user", "input": {}}}]})
    # 8, 9 (user replies with toolResult, then assistant responds)
    history.append({"role": "user", "content": [{"toolResult": {"toolUseId": "1", "status": "success", "content": [{"text": "result"}]}}]})
    history.append({"role": "assistant", "content": [{"text": "Reply 3"}]})
    # 10, 11
    history.append({"role": "user", "content": [{"text": "Msg 4"}]})
    history.append({"role": "assistant", "content": [{"text": "Reply 4"}]})
    # 12, 13
    history.append({"role": "user", "content": [{"text": "Msg 5"}]})
    history.append({"role": "assistant", "content": [{"text": "Reply 5"}]})
    
    assert len(history) == 14
    
    # Trigger chat which will compress
    res = orchestrator.chat(history)
    assert res["content"][0]["text"] == "Pushed memory!"
    
    # Since index 8 was a toolResult, the code should have skipped it and split at index 10
    # Meaning history should have had messages 0-9 compressed and pruned.
    # The remaining messages starting at index 10 (Msg 4) should remain, plus the new reply.
    # Total remaining messages in history: Msg 4 (10), Reply 4 (11), Msg 5 (12), Reply 5 (13) -> 4 messages,
    # plus the new assistant reply appended by orchestrator.chat, making 5 messages total.
    assert len(history) == 5
    assert history[0]["role"] == "user"
    assert history[0]["content"][0]["text"] == "Msg 4"

