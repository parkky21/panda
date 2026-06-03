import os
import json
import subprocess
from rich.console import Console

console = Console()

class SkillsManager:
    """
    Manages saving, listing, and executing custom agent skills (Python/bash).
    Includes a safety gate requesting terminal confirmation before executing any skill.
    """
    def __init__(self, skills_dir: str):
        self.skills_dir = os.path.abspath(skills_dir)
        os.makedirs(self.skills_dir, exist_ok=True)
        self.meta_path = os.path.join(self.skills_dir, "skills_meta.json")
        self._load_meta()

    def _load_meta(self):
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.meta = json.load(f)
            except Exception:
                self.meta = {}
        else:
            self.meta = {}

    def _save_meta(self):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2)

    def save_skill(self, name: str, code: str, description: str) -> str:
        """
        Saves a Python or Bash skill script and its description.
        """
        # Security: Clean the file name
        import re
        if not name or not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return "Error: Invalid skill name."
        clean_name = name
            
        # Determine language/extension
        ext = ".py"
        if code.strip().startswith("#!/bin/bash") or code.strip().startswith("#!/bin/sh"):
            ext = ".sh"
            
        file_name = f"{clean_name}{ext}"
        file_path = os.path.join(self.skills_dir, file_name)
        
        # Write script
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Make script executable if it's a bash script
        if ext == ".sh":
            try:
                os.chmod(file_path, 0o755)
            except Exception:
                pass
                
        # Update metadata
        self.meta[clean_name] = {
            "file": file_name,
            "description": description,
            "type": "python" if ext == ".py" else "bash"
        }
        self._save_meta()
        
        return f"Successfully saved skill '{clean_name}' (type: {self.meta[clean_name]['type']})."

    def list_skills(self) -> dict:
        """
        Returns a dictionary of all available skills.
        """
        return self.meta

    def run_skill(self, name: str, args: list = None) -> str:
        """
        Runs a saved skill after getting user approval via terminal.
        """
        if name not in self.meta:
            return f"Error: Skill '{name}' not found."
            
        skill_info = self.meta[name]
        file_path = os.path.join(self.skills_dir, skill_info["file"])
        
        if not os.path.exists(file_path):
            return f"Error: Skill script file not found at {file_path}."
            
        args = args or []
        
        # Security Prompt: Always request approval before running code
        auto_approve = os.getenv("AUTO_APPROVE_SKILLS", "false").lower() in ("true", "1", "yes")
        if auto_approve:
            console.print(f"\n[bold green]✓ AUTO-APPROVED SKILL EXECUTION: '{name}'[/bold green]")
        else:
            console.print(f"\n[bold yellow]⚠️  SECURITY GATE: The agent wants to execute the skill '{name}'[/bold yellow]")
            console.print(f"Description: {skill_info['description']}")
            console.print(f"Arguments: {args}")
            
            # We perform terminal input approval
            choice = input("Do you want to run this skill? (y/N): ").strip().lower()
            if choice not in ("y", "yes"):
                return "Execution Aborted: User denied permission to run the skill."
            
        # Execute script
        try:
            if skill_info["type"] == "python":
                cmd = ["python", file_path] + [str(a) for a in args]
            else:
                cmd = [file_path] + [str(a) for a in args]
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Safety timeout
            )
            
            if result.returncode == 0:
                return f"Skill '{name}' executed successfully.\nOutput:\n{result.stdout}"
            else:
                return f"Skill '{name}' failed with exit code {result.returncode}.\nError:\n{result.stderr}\nOutput:\n{result.stdout}"
                
        except subprocess.TimeoutExpired:
            return f"Error: Skill '{name}' execution timed out after 30 seconds."
        except Exception as e:
            return f"Error executing skill: {str(e)}"
