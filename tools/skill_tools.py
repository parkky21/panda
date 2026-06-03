# Tool implementations and schemas for the Skills System

def save_skill(skills_manager, name: str, code: str, description: str) -> str:
    """
    Saves a custom Python or Bash skill script to execute workflows.
    """
    try:
        return skills_manager.save_skill(name, code, description)
    except Exception as e:
        return f"Error saving skill: {str(e)}"

def run_skill(skills_manager, name: str, args: list = None, background: bool = False) -> str:
    """
    Executes a saved skill script with the provided arguments.
    """
    try:
        if background:
            import threading
            def bg_run():
                output = skills_manager.run_skill(name, args)
                notify = getattr(skills_manager, "notify_callback", None)
                if notify:
                    notify(f"🔔 **Background Task '{name}' Finished:**\n{output}")
            threading.Thread(target=bg_run, daemon=True).start()
            return f"Skill '{name}' successfully started in the background. I will notify you when it finishes."
        return skills_manager.run_skill(name, args)
    except Exception as e:
        return f"Error executing skill: {str(e)}"

def list_skills(skills_manager) -> str:
    """
    Lists all saved skills available to the agent.
    """
    try:
        skills = skills_manager.list_skills()
        if not skills:
            return "No skills saved yet."
        import json
        return json.dumps(skills, indent=2)
    except Exception as e:
        return f"Error listing skills: {str(e)}"


# Maps tool names to Python implementations
SKILL_TOOL_IMPLEMENTATIONS = {
    "save_skill": save_skill,
    "run_skill": run_skill,
    "list_skills": list_skills
}

# Schemas for Bedrock Converse API
BEDROCK_SKILL_TOOL_CONFIGS = [
    {
        "toolSpec": {
            "name": "save_skill",
            "description": "Saves a reusable Python or Bash script to automate a workflow (e.g. fetching API data, running git commands, parsing files). The file is stored in a 'skills/' directory.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Unique name of the skill (alphanumeric and underscores/hyphens only)."
                        },
                        "code": {
                            "type": "string",
                            "description": "The complete runnable Python code (default) or Bash script starting with '#!/bin/bash'."
                        },
                        "description": {
                            "type": "string",
                            "description": "A clear description of what this skill does and the arguments it accepts."
                        }
                    },
                    "required": ["name", "code", "description"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "run_skill",
            "description": "Runs a saved custom skill script with optional arguments. Execution requires user terminal confirmation. Set 'background' to true to run long-running scripts asynchronously in the background so you don't block the conversation flow.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the skill to execute."
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of string arguments to pass to the script."
                        },
                        "background": {
                            "type": "boolean",
                            "description": "If true, runs the script asynchronously in the background and notifies the user via the chat when it completes."
                        }
                    },
                    "required": ["name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "list_skills",
            "description": "Returns a list of all saved skills, their descriptions, and language types.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    }
]
