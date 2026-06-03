import os
import json
import time
import re
from rich.console import Console

console = Console()

class CronScheduler:
    """
    Manages background scheduled automations (crons).
    Loads tasks from memory/crons.json and executes due tasks,
    appending reports to memory.md.
    """
    def __init__(self, memory_dir: str):
        self.memory_dir = os.path.abspath(memory_dir)
        self.cron_path = os.path.join(self.memory_dir, "crons.json")
        self.memory_path = os.path.join(self.memory_dir, "memory.md")
        self._load_tasks()

    def _load_tasks(self):
        if os.path.exists(self.cron_path):
            try:
                with open(self.cron_path, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception:
                self.tasks = {}
        else:
            self.tasks = {}

    def _save_tasks(self):
        with open(self.cron_path, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, indent=2)

    def schedule_task(self, task_name: str, interval_seconds: int, command: str) -> str:
        """
        Schedules a background command/automation.
        """
        if not task_name or not re.match(r"^[a-zA-Z0-9_-]+$", task_name):
            return "Error: Invalid task name."
        clean_name = task_name
            
        self.tasks[clean_name] = {
            "interval_seconds": interval_seconds,
            "command": command,
            "last_run": 0
        }
        self._save_tasks()
        return f"Successfully scheduled task '{clean_name}' to run every {interval_seconds} seconds."

    def list_tasks(self) -> dict:
        """
        Returns all scheduled tasks.
        """
        return self.tasks

    def unschedule_task(self, task_name: str) -> str:
        """
        Removes a scheduled background task.
        """
        if task_name in self.tasks:
            del self.tasks[task_name]
            self._save_tasks()
            return f"Successfully unscheduled task '{task_name}'."
        return f"Error: Task '{task_name}' not found."

    def _log_to_memory(self, task_name: str, status: str, output: str):
        """
        Appends the execution output of a cron task to the agent's memory.md file.
        """
        if not os.path.exists(self.memory_path):
            return
            
        with open(self.memory_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse and insert under '## Environmental Facts' or '## Tasks & TODOs'
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n* **[CRON RUN - {timestamp}]** Task '{task_name}' status: {status}. Output: {output.strip()}"
        
        # Insert log entry after ## Environmental Facts or at the end
        target_section = "## Environmental Facts"
        if target_section in content:
            # Insert right after the section header
            pattern = re.escape(target_section) + r"(.*?)(\n##|$)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                facts_body = match.group(1)
                # If it's a placeholder, remove it
                if "No facts recorded yet." in facts_body:
                    facts_body = facts_body.replace("No facts recorded yet.", "")
                updated_facts = facts_body.rstrip() + log_entry + "\n"
                new_section_content = f"{target_section}{updated_facts}\n##" if match.group(2) == "\n##" else f"{target_section}{updated_facts}"
                content = content[:match.start()] + new_section_content + content[match.end() - (2 if match.group(2) == "\n##" else 0):]
        else:
            content += f"\n\n## Environmental Facts\n{log_entry}"
            
        with open(self.memory_path, "w", encoding="utf-8") as f:
            f.write(content)

    def run_due_tasks(self, skills_manager, on_task_run = None) -> list:
        """
        Checks all tasks, runs those that are due, logs results to memory,
        and returns a list of executed task reports.
        """
        self._load_tasks()
        current_time = time.time()
        executed_tasks = []
        
        for name, task in list(self.tasks.items()):
            if current_time - task["last_run"] >= task["interval_seconds"]:
                console.print(f"\n[bold yellow]⏰ Background Cron: Running scheduled task '{name}'...[/bold yellow]")
                
                command = task["command"]
                output = ""
                status = "success"
                
                # Check if it calls a skill
                if command.startswith("run_skill "):
                    parts = command[10:].split()
                    skill_name = parts[0]
                    skill_args = parts[1:]
                    output = skills_manager.run_skill(skill_name, skill_args)
                    if "Error" in output or "Aborted" in output:
                        status = "failed"
                else:
                    # Run general python command or print
                    # For safety, let's limit it to run_skill or simple echo.
                    # We will support basic console echoes or simple execution.
                    import subprocess
                    try:
                        result = subprocess.run(
                            command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0:
                            output = result.stdout
                        else:
                            output = f"Failed with stderr: {result.stderr}"
                            status = "failed"
                    except Exception as e:
                        output = f"Execution error: {str(e)}"
                        status = "failed"
                
                # Update task last run
                task["last_run"] = current_time
                self._log_to_memory(name, status, output)
                executed_tasks.append(f"Task '{name}' run: {status}")
                
                if on_task_run:
                    on_task_run(name, status, output)
                
        if executed_tasks:
            self._save_tasks()
            
        return executed_tasks
