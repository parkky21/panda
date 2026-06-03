import boto3
import json
import logging
from agent.memory_manager import MemoryManager
from tools.memory_tools import TOOL_IMPLEMENTATIONS, BEDROCK_TOOL_CONFIGS

logger = logging.getLogger(__name__)

class PandaOrchestrator:
    """
    Decoupled orchestrator that manages conversations with Bedrock,
    constructs the dynamic system prompt, and executes tool calls.
    """
    def __init__(self, memory_dir: str, model_id: str = "moonshotai.kimi-k2.5", region_name: str = "us-east-1"):
        self.memory_manager = MemoryManager(memory_dir)
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        
    def _build_system_prompt(self) -> str:
        """Constructs the system prompt dynamically from the memory files."""
        soul = self.memory_manager.read_soul()
        tools_desc = self.memory_manager.read_tools_description()
        user_profile = self.memory_manager.read_user_profile()
        
        system_prompt = f"""{soul}

---
# YOUR CAPABILITIES (READ-ONLY)
{tools_desc}

---
# CORE CONTEXT ABOUT THE USER (KNOWN EVERY CHAT)
{user_profile}

---
# OPERATIONAL INSTRUCTIONS
1. Check your Long Term Memory Index (`LongTermMemory.md`) if the user references past details, childhood, career, or specific events.
2. If you learn general, permanent facts about the user (their name, coffee preferences, location, birth date, personality traits), write/update the user profile using `update_user_profile`.
3. If you learn specific, detailed stories (like a childhood memory or a detailed career history), write a new memory node (e.g. `childhood`, `career`) using `write_memory_node` and then link it from `LongTermMemory` using `link_memory_nodes`.
4. Always act in accordance with your Soul: be playful, optimistic, but completely straightforward and honest. Never sugarcoat information.
"""
        return system_prompt

    def chat(self, messages_history: list, on_tool_call_start=None, on_tool_call_end=None) -> dict:
        """
        Sends the message history to Bedrock. Handles the tool-use loop
        by calling the requested Python functions and sending the results back.
        
        Args:
            messages_history: List of conversation messages (modified in place)
            on_tool_call_start: Optional callback function(tool_name, tool_args)
            on_tool_call_end: Optional callback function(tool_name, result)
            
        Returns:
            The final assistant response message structure.
        """
        system_prompt = self._build_system_prompt()
        
        # Bedrock Converse API tool config
        tool_config = {
            "tools": BEDROCK_TOOL_CONFIGS
        }
        
        # Limit loops to prevent infinite tool calling recursion
        max_loops = 6
        loop_count = 0
        
        while loop_count < max_loops:
            loop_count += 1
            
            # Request response from Bedrock
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages_history,
                system=[{"text": system_prompt}],
                toolConfig=tool_config
            )
            
            output_message = response["output"]["message"]
            messages_history.append(output_message)
            
            # Check if Bedrock wants to invoke a tool
            stop_reason = response.get("stopReason")
            if stop_reason == "tool_use":
                tool_requests = response["output"]["message"]["content"]
                
                tool_results = []
                for content_block in tool_requests:
                    if "toolUse" in content_block:
                        tool_use = content_block["toolUse"]
                        tool_use_id = tool_use["toolUseId"]
                        tool_name = tool_use["name"]
                        tool_args = tool_use["input"]
                        
                        # Trigger start callback if provided
                        if on_tool_call_start:
                            on_tool_call_start(tool_name, tool_args)
                            
                        # Execute the tool
                        tool_func = TOOL_IMPLEMENTATIONS.get(tool_name)
                        if tool_func:
                            result = tool_func(self.memory_manager, **tool_args)
                        else:
                            result = f"Error: Tool '{tool_name}' not implemented."
                            
                        # Trigger end callback if provided
                        if on_tool_call_end:
                            on_tool_call_end(tool_name, result)
                            
                        # Append result in Bedrock Converse format
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"text": str(result)}],
                                "status": "success"
                            }
                        })
                
                # Append tool results as a user turn
                messages_history.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Loop back to send tool results to Bedrock
                continue
            else:
                # Finished generating text, break the loop
                return output_message
                
        raise RuntimeError("Agent reached maximum tool call iterations without responding.")
