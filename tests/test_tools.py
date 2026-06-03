import pytest
from unittest.mock import MagicMock, patch

from tools.memory_tools import (
    read_user, write_user, read_memory, write_memory,
    MEMORY_TOOL_IMPLEMENTATIONS, BEDROCK_MEMORY_TOOL_CONFIGS
)
from tools.skill_tools import (
    save_skill, run_skill, list_skills,
    SKILL_TOOL_IMPLEMENTATIONS, BEDROCK_SKILL_TOOL_CONFIGS
)
from tools.cron_tools import (
    schedule_task, list_scheduled_tasks, unschedule_task,
    CRON_TOOL_IMPLEMENTATIONS, BEDROCK_CRON_TOOL_CONFIGS
)
from tools.subagent_tools import (
    spawn_subagent,
    SUBAGENT_TOOL_IMPLEMENTATIONS, BEDROCK_SUBAGENT_TOOL_CONFIGS
)

def test_memory_tools():
    mock_manager = MagicMock()
    
    # Read user
    mock_manager.read_user.return_value = "User Profile Data"
    res = read_user(mock_manager)
    assert res == "User Profile Data"
    mock_manager.read_user.assert_called_once()
    
    # Write user
    mock_manager.write_user.return_value = "Success"
    res = write_user(mock_manager, "new content")
    assert res == "Success"
    mock_manager.write_user.assert_called_once_with("new content")
    
    # Read memory
    mock_manager.read_memory.return_value = "Memory Data"
    res = read_memory(mock_manager)
    assert res == "Memory Data"
    mock_manager.read_memory.assert_called_once()
    
    # Write memory
    mock_manager.write_memory.return_value = "Success Memory"
    res = write_memory(mock_manager, "new memory content")
    assert res == "Success Memory"
    mock_manager.write_memory.assert_called_once_with("new memory content")
    
    # Assert configs and maps are set
    assert "read_user" in MEMORY_TOOL_IMPLEMENTATIONS
    assert len(BEDROCK_MEMORY_TOOL_CONFIGS) == 4

def test_skill_tools():
    mock_manager = MagicMock()
    
    # Save skill
    mock_manager.save_skill.return_value = "Saved skill"
    res = save_skill(mock_manager, "test", "code", "desc")
    assert res == "Saved skill"
    mock_manager.save_skill.assert_called_once_with("test", "code", "desc")
    
    # Run skill
    mock_manager.run_skill.return_value = "Run output"
    res = run_skill(mock_manager, "test", ["arg"])
    assert res == "Run output"
    mock_manager.run_skill.assert_called_once_with("test", ["arg"])
    
    # Run skill in background
    mock_manager.run_skill.reset_mock()
    res_bg = run_skill(mock_manager, "test", ["arg"], background=True)
    assert "started in the background" in res_bg
    import time
    for _ in range(20):
        if mock_manager.run_skill.called:
            break
        time.sleep(0.01)
    mock_manager.run_skill.assert_called_once_with("test", ["arg"])
    
    # List skills
    mock_manager.list_skills.return_value = {"test": {}}
    res = list_skills(mock_manager)
    assert "test" in res
    mock_manager.list_skills.assert_called_once()
    
    assert "save_skill" in SKILL_TOOL_IMPLEMENTATIONS
    assert len(BEDROCK_SKILL_TOOL_CONFIGS) == 3

def test_cron_tools():
    mock_manager = MagicMock()
    
    # Schedule task
    mock_manager.schedule_task.return_value = "Scheduled"
    res = schedule_task(mock_manager, "task", 60, "cmd")
    assert res == "Scheduled"
    mock_manager.schedule_task.assert_called_once_with("task", 60, "cmd")
    
    # List tasks
    mock_manager.list_tasks.return_value = {"task": {}}
    res = list_scheduled_tasks(mock_manager)
    assert "task" in res
    mock_manager.list_tasks.assert_called_once()

    # Unschedule task
    mock_manager.unschedule_task.return_value = "Unscheduled"
    res = unschedule_task(mock_manager, "task")
    assert res == "Unscheduled"
    mock_manager.unschedule_task.assert_called_once_with("task")
    
    assert "schedule_task" in CRON_TOOL_IMPLEMENTATIONS
    assert "unschedule_task" in CRON_TOOL_IMPLEMENTATIONS
    assert len(BEDROCK_CRON_TOOL_CONFIGS) == 3

@patch('boto3.client')
@patch('agent.config.AgentConfig.get_model_id', return_value="mock-model")
@patch('agent.config.AgentConfig.get_aws_region', return_value="us-east-1")
def test_subagent_tools(mock_region, mock_model, mock_boto):
    # Mock boto3 converse call
    mock_client = MagicMock()
    mock_boto.return_value = mock_client
    mock_client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "Sub-agent result"}]
            }
        }
    }
    
    mock_orchestrator = MagicMock()
    res = spawn_subagent(mock_orchestrator, "Solve a task", "Optional context")
    assert res == "Sub-agent result"
    
    mock_client.converse.assert_called_once()

    # Test background subagent
    mock_client.converse.reset_mock()
    res_bg = spawn_subagent(mock_orchestrator, "Solve in bg", background=True)
    assert "started in the background" in res_bg
    
    # Wait for thread to run
    import time
    for _ in range(20):
        if mock_client.converse.called:
            break
        time.sleep(0.01)
    mock_client.converse.assert_called_once()
    
    assert "spawn_subagent" in SUBAGENT_TOOL_IMPLEMENTATIONS
    assert len(BEDROCK_SUBAGENT_TOOL_CONFIGS) == 1
