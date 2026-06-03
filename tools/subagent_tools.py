import boto3
from agent.config import AgentConfig

def _run_subagent(task: str, context: str = None) -> str:
    client = boto3.client("bedrock-runtime", region_name=AgentConfig.get_aws_region())
    model_id = AgentConfig.get_model_id()
    
    subagent_system_prompt = (
        "You are an expert sub-agent helper. Your job is to complete a specific task "
        "assigned by the main assistant. Deliver the result as clearly and directly as possible. "
        "Do not output conversational greetings, wraps, or small talk. Focus only on the solution."
    )
    
    prompt = f"TASK TO COMPLETE:\n{task}"
    if context:
        prompt += f"\n\nCONTEXT:\n{context}"
        
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    
    try:
        response = client.converse(
            modelId=model_id,
            messages=messages,
            system=[{"text": subagent_system_prompt}]
        )
        
        result_text = "".join(
            block.get("text", "") 
            for block in response["output"]["message"]["content"] 
            if "text" in block
        )
        return result_text
        
    except Exception as e:
        return f"Error executing sub-agent task: {str(e)}"

def spawn_subagent(orchestrator, task: str, context: str = None, background: bool = False) -> str:
    """
    Spawns an isolated sub-agent to perform a sub-task and return the result.
    """
    if background:
        import threading
        def bg_run():
            result = _run_subagent(task, context)
            notify = getattr(orchestrator, "notify_callback", None)
            if notify:
                notify(f"🤖 **Sub-agent Background Task Completed!**\n**Result:**\n{result}")
        threading.Thread(target=bg_run, daemon=True).start()
        return "Sub-agent successfully started in the background. I will notify you when it finishes."
        
    return _run_subagent(task, context)


# Maps tool name to implementation
SUBAGENT_TOOL_IMPLEMENTATIONS = {
    "spawn_subagent": spawn_subagent
}

# Schemas for Bedrock Converse API
BEDROCK_SUBAGENT_TOOL_CONFIGS = [
    {
        "toolSpec": {
            "name": "spawn_subagent",
            "description": "Spawns an isolated helper sub-agent to solve a complex sub-task, perform a calculation, format text, or summarize data. Set 'background' to true to run the sub-agent asynchronously in the background so you don't block the conversation flow.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The specific task description for the helper sub-agent to execute."
                        },
                        "context": {
                            "type": "string",
                            "description": "Any additional background context, data, or files contents required to solve the task."
                        },
                        "background": {
                            "type": "boolean",
                            "description": "If true, runs the sub-agent asynchronously in the background and notifies the user via the chat when it completes."
                        }
                    },
                    "required": ["task"]
                }
            }
        }
    }
]
