import os
import time
import pytest
from unittest.mock import MagicMock, patch
from agent.scheduler import CronScheduler

def test_schedule_and_list_tasks(temp_memory_dir):
    scheduler = CronScheduler(temp_memory_dir)
    
    # Schedule task
    res = scheduler.schedule_task(
        task_name="test_cron",
        interval_seconds=60,
        command="run_skill check_site"
    )
    assert "Successfully scheduled task" in res
    
    # List tasks and verify json
    tasks = scheduler.list_tasks()
    assert "test_cron" in tasks
    assert tasks["test_cron"]["interval_seconds"] == 60
    assert tasks["test_cron"]["command"] == "run_skill check_site"
    
    assert os.path.exists(os.path.join(temp_memory_dir, "crons.json"))

def test_invalid_task_name(temp_memory_dir):
    scheduler = CronScheduler(temp_memory_dir)
    res = scheduler.schedule_task(
        task_name="../../../bad_cron",
        interval_seconds=10,
        command="echo"
    )
    assert "Error: Invalid task name" in res

def test_log_to_memory_file(temp_memory_dir):
    scheduler = CronScheduler(temp_memory_dir)
    scheduler._log_to_memory("backup_task", "success", "All files backed up.")
    
    with open(scheduler.memory_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Task 'backup_task' status: success" in content
    assert "Output: All files backed up." in content

@patch('time.time', return_value=1000)
def test_run_due_tasks_success(mock_time, temp_memory_dir):
    scheduler = CronScheduler(temp_memory_dir)
    scheduler.schedule_task("due_task", 10, "run_skill test_skill")
    
    # Set last_run to 980 so it's due (1000 - 980 = 20 >= 10)
    scheduler.tasks["due_task"]["last_run"] = 980
    scheduler._save_tasks()
    
    # Mock skills manager run_skill call
    mock_skills = MagicMock()
    mock_skills.run_skill.return_value = "Skill executed OK"
    
    executed = scheduler.run_due_tasks(mock_skills)
    assert "Task 'due_task' run: success" in executed
    
    # Verify last_run was updated to 1000
    assert scheduler.tasks["due_task"]["last_run"] == 1000
    mock_skills.run_skill.assert_called_once_with("test_skill", [])
    
    # Check log in memory.md
    with open(scheduler.memory_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Task 'due_task' status: success" in content

@patch('time.time', return_value=1000)
def test_run_due_tasks_not_due(mock_time, temp_memory_dir):
    scheduler = CronScheduler(temp_memory_dir)
    scheduler.schedule_task("not_due_task", 60, "echo")
    
    # Set last_run to 980 (1000 - 980 = 20 < 60)
    scheduler.tasks["not_due_task"]["last_run"] = 980
    scheduler._save_tasks()
    
    mock_skills = MagicMock()
    executed = scheduler.run_due_tasks(mock_skills)
    assert len(executed) == 0
    assert scheduler.tasks["not_due_task"]["last_run"] == 980

def test_unschedule_task(temp_memory_dir):
    scheduler = CronScheduler(temp_memory_dir)
    scheduler.schedule_task("task_to_remove", 30, "echo")
    assert "task_to_remove" in scheduler.list_tasks()
    
    # Unschedule
    res = scheduler.unschedule_task("task_to_remove")
    assert "Successfully unscheduled" in res
    assert "task_to_remove" not in scheduler.list_tasks()
    
    # Non-existent
    res_err = scheduler.unschedule_task("nonexistent")
    assert "Error: Task 'nonexistent' not found." in res_err
