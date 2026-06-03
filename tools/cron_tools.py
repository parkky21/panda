# Tool implementations and schemas for the Cron Scheduler System

def schedule_task(scheduler, task_name: str, interval_seconds: int, command: str) -> str:
    """
    Schedules a background command or skill to run periodically.
    """
    try:
        return scheduler.schedule_task(task_name, interval_seconds, command)
    except Exception as e:
        return f"Error scheduling task: {str(e)}"

def list_scheduled_tasks(scheduler) -> str:
    """
    Lists all scheduled background tasks and their intervals.
    """
    try:
        tasks = scheduler.list_tasks()
        if not tasks:
            return "No background tasks scheduled."
        import json
        return json.dumps(tasks, indent=2)
    except Exception as e:
        return f"Error listing scheduled tasks: {str(e)}"

def unschedule_task(scheduler, task_name: str) -> str:
    """
    Removes a scheduled background task so it stops running.
    """
    try:
        return scheduler.unschedule_task(task_name)
    except Exception as e:
        return f"Error unscheduling task: {str(e)}"


# Maps tool names to Python implementations
CRON_TOOL_IMPLEMENTATIONS = {
    "schedule_task": schedule_task,
    "list_scheduled_tasks": list_scheduled_tasks,
    "unschedule_task": unschedule_task
}

# Schemas for Bedrock Converse API
BEDROCK_CRON_TOOL_CONFIGS = [
    {
        "toolSpec": {
            "name": "schedule_task",
            "description": "Schedules a task/command to run in the background at regular intervals (e.g. check a website status every 60 seconds). You can trigger a skill by using the command format: 'run_skill <skill_name> <args>'. Output of execution is logged to memory.md.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "Unique identifier of the task (alphanumeric and underscores/hyphens)."
                        },
                        "interval_seconds": {
                            "type": "integer",
                            "description": "Frequency of run in seconds (e.g., 60, 3600)."
                        },
                        "command": {
                            "type": "string",
                            "description": "The command or script to run (e.g. 'run_skill check_site google.com')."
                        }
                    },
                    "required": ["task_name", "interval_seconds", "command"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "list_scheduled_tasks",
            "description": "Lists all background tasks that are currently active and their intervals.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "unschedule_task",
            "description": "Removes a scheduled background task by name, stopping it from running in the future.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "The unique name of the task to remove."
                        }
                    },
                    "required": ["task_name"]
                }
            }
        }
    }
]
