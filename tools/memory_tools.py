import logging

# We define the tool functions that can be called by Bedrock.
# Each function will accept the memory_manager as the first argument, followed by the args from the model.

def read_memory_node(memory_manager, node_name: str) -> str:
    """
    Retrieve the content of a specific memory node from the memory directory.
    """
    try:
        return memory_manager.read_node(node_name)
    except Exception as e:
        return f"Error reading memory node: {str(e)}"

def write_memory_node(memory_manager, node_name: str, content: str) -> str:
    """
    Create a new memory node or overwrite an existing one with new structured information.
    """
    try:
        return memory_manager.write_node(node_name, content)
    except Exception as e:
        return f"Error writing memory node: {str(e)}"

def link_memory_nodes(memory_manager, parent_node: str, child_node: str, link_description: str) -> str:
    """
    Link a parent memory node to a child memory node by adding a markdown link to the parent file.
    """
    try:
        return memory_manager.link_nodes(parent_node, child_node, link_description)
    except Exception as e:
        return f"Error linking memory nodes: {str(e)}"

def update_user_profile(memory_manager, content: str) -> str:
    """
    Overwrite or append details in the user profile file to keep information about the user accurate.
    """
    try:
        return memory_manager.update_user_profile(content)
    except Exception as e:
        return f"Error updating user profile: {str(e)}"


# This dictionary maps tool names to their actual Python implementations.
TOOL_IMPLEMENTATIONS = {
    "read_memory_node": read_memory_node,
    "write_memory_node": write_memory_node,
    "link_memory_nodes": link_memory_nodes,
    "update_user_profile": update_user_profile
}

# This list defines the schemas that will be sent to the Bedrock Converse API.
# It matches the expected JSON structure for toolConfig.tools in Bedrock Converse API.
BEDROCK_TOOL_CONFIGS = [
    {
        "toolSpec": {
            "name": "read_memory_node",
            "description": "Reads the content of a specific memory node file (e.g., 'LongTermMemory.md', 'childhood.md', 'hobbies.md') to retrieve historical context or information about the user.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "node_name": {
                            "type": "string",
                            "description": "The name of the memory node file to read. (e.g., 'LongTermMemory', 'childhood', 'career')"
                        }
                    },
                    "required": ["node_name"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "write_memory_node",
            "description": "Creates a new memory node file or completely updates an existing one (e.g. 'childhood', 'work') with structured information about the user's life, preferences, or details they share.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "node_name": {
                            "type": "string",
                            "description": "The name of the memory node file to create or write. (e.g., 'childhood', 'career')"
                        },
                        "content": {
                            "type": "string",
                            "description": "The full Markdown content to write to this memory node."
                        }
                    },
                    "required": ["node_name", "content"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "link_memory_nodes",
            "description": "Links a parent memory node file to a child memory node file by adding a markdown link to the parent file. This is how the long-term memory graph structure is formed.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "parent_node": {
                            "type": "string",
                            "description": "The name of the parent node file to append the link to (e.g., 'LongTermMemory.md' or 'career.md')."
                        },
                        "child_node": {
                            "type": "string",
                            "description": "The name of the child node file being linked to (e.g., 'childhood.md')."
                        },
                        "link_description": {
                            "type": "string",
                            "description": "A short, readable description of the link to display in the markdown file."
                        }
                    },
                    "required": ["parent_node", "child_node", "link_description"]
                }
            }
        }
    },
    {
        "toolSpec": {
            "name": "update_user_profile",
            "description": "Overwrites the user_profile.md file containing the general background facts about the user that are injected into every chat. Use this to save permanent details like user's name, preferences, core background, etc.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The entire new Markdown content for the user profile."
                        }
                    },
                    "required": ["content"]
                }
            }
        }
    }
]
