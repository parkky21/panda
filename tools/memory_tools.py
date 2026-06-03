# Tool implementations and schemas for Flat Memory System (user.md, memory.md)

def read_user(memory_manager) -> str:
    """
    Retrieve the content of the user profile file (user.md) which contains preferences.
    """
    try:
        return memory_manager.read_user()
    except Exception as e:
        return f"Error reading user profile: {str(e)}"

def write_user(memory_manager, content: str) -> str:
    """
    Overwrite or completely update the user.md file with new structured information about the user.
    """
    try:
        return memory_manager.write_user(content)
    except Exception as e:
        return f"Error writing user profile: {str(e)}"

def read_memory(memory_manager) -> str:
    """
    Retrieve the content of the agent memory file (memory.md) which contains notes, tasks, and crons log.
    """
    try:
        return memory_manager.read_memory()
    except Exception as e:
        return f"Error reading memory: {str(e)}"

def write_memory(memory_manager, content: str) -> str:
    """
    Overwrite or completely update the memory.md file with structured notes, facts, and tasks.
    """
    try:
        return memory_manager.write_memory(content)
    except Exception as e:
        return f"Error writing memory: {str(e)}"


# Maps tool names to Python implementations
MEMORY_TOOL_IMPLEMENTATIONS = {
    "read_user": read_user,
    "write_user": write_user,
    "read_memory": read_memory,
    "write_memory": write_memory
}

# Schemas for Bedrock Converse API
BEDROCK_MEMORY_TOOL_CONFIGS = [
    {
        "toolSpec": {
            "name": "read_user",
            "description": "Reads the user.md file containing structured facts, preferences, and communication style of the user.",
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
            "name": "write_user",
            "description": "Completely updates the user.md file. Use this when you need to restructure, add, or refine facts (e.g. name, preferences) under their appropriate sections (e.g. ## Personal Info, ## Preferences, ## Communication Style). Keep the formatting clean.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The complete updated Markdown content for user.md"
                        }
                    },
                    "required": ["content"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "read_memory",
            "description": "Reads the memory.md file containing structured agent notes, tasks & TODOs, environmental facts, and cron logs.",
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
            "name": "write_memory",
            "description": "Completely updates the memory.md file. Use this to organize facts, add tasks, or add notes under their appropriate sections (e.g. ## Environmental Facts, ## Tasks & TODOs, ## General Notes). Keep the formatting clean.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The complete updated Markdown content for memory.md"
                        }
                    },
                    "required": ["content"]
                }
            }
        }
    }
]
