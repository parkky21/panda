import boto3
import json
import logging
import os
import re
import time
from agent.memory_manager import MemoryManager
from agent.skills_manager import SkillsManager
from agent.scheduler import CronScheduler
from agent.config import AgentConfig

from tools.memory_tools import MEMORY_TOOL_IMPLEMENTATIONS, BEDROCK_MEMORY_TOOL_CONFIGS
from tools.skill_tools import SKILL_TOOL_IMPLEMENTATIONS, BEDROCK_SKILL_TOOL_CONFIGS
from tools.cron_tools import CRON_TOOL_IMPLEMENTATIONS, BEDROCK_CRON_TOOL_CONFIGS
from tools.subagent_tools import SUBAGENT_TOOL_IMPLEMENTATIONS, BEDROCK_SUBAGENT_TOOL_CONFIGS

logger = logging.getLogger(__name__)

class PandaOrchestrator:
    """
    Orchestrates the Panda agent conversation loop.
    Maintains the soul, user, and memory contexts, exposes skill and cron tools,
    runs a self-reflection pass on session end, and performs context compression.
    """
    def __init__(self, memory_dir: str, skills_dir: str = "./skills", model_id: str = None, region_name: str = None, notify_callback = None):
        self.model_id = model_id or AgentConfig.get_model_id()
        region = region_name or AgentConfig.get_aws_region()
        self.client = boto3.client("bedrock-runtime", region_name=region)
        
        self.memory_manager = MemoryManager(memory_dir)
        self.skills_manager = SkillsManager(skills_dir)
        self.skills_manager.notify_callback = notify_callback
        self.scheduler = CronScheduler(memory_dir)
        
        # Track running conversation context summary
        self.conversation_summary = ""
        
        # Merge tool implementations and configurations
        self.tool_implementations = {}
        self.tool_implementations.update(MEMORY_TOOL_IMPLEMENTATIONS)
        self.tool_implementations.update(SKILL_TOOL_IMPLEMENTATIONS)
        self.tool_implementations.update(CRON_TOOL_IMPLEMENTATIONS)
        self.tool_implementations.update(SUBAGENT_TOOL_IMPLEMENTATIONS)
        
        self.tool_configs = []
        self.tool_configs.extend(BEDROCK_MEMORY_TOOL_CONFIGS)
        self.tool_configs.extend(BEDROCK_SKILL_TOOL_CONFIGS)
        self.tool_configs.extend(BEDROCK_CRON_TOOL_CONFIGS)
        self.tool_configs.extend(BEDROCK_SUBAGENT_TOOL_CONFIGS)

    def _build_system_prompt(self) -> str:
        """Constructs the system prompt dynamically, injecting flat memories, crons, and skills."""
        soul = self.memory_manager.read_soul()
        user = self.memory_manager.read_user()
        memory = self.memory_manager.read_memory()
        
        skills = self.skills_manager.list_skills()
        skills_str = json.dumps(skills, indent=2) if skills else "No custom skills created yet."
        
        crons = self.scheduler.list_tasks()
        crons_str = json.dumps(crons, indent=2) if crons else "No background tasks scheduled."
        
        system_prompt = f"""{soul}

---
# 👤 USER PROFILE (LOADED EVERY CHAT)
{user}

---
# 🧠 AGENT MEMORY (LOADED EVERY CHAT)
{memory}

---
# 🛠️ AVAILABLE PROCEDURAL SKILLS
The user or you can run these custom skills via the `run_skill` tool:
{skills_str}

---
# ⏰ ACTIVE BACKGROUND CRONS
{crons_str}
"""

        # Inject conversation summary if it exists
        if self.conversation_summary:
            system_prompt += f"""
---
# 📜 SUMMARY OF EARLIER CONVERSATION
Panda, you have compressed the older part of this chat. Here is the summary of what was discussed:
{self.conversation_summary}
"""

        system_prompt += """
---
# OPERATIONAL INSTRUCTIONS
1. Be playful, optimistic, but completely straightforward, blunt, and honest. Never sugarcoat.
2. If you learn general, permanent facts about the user (e.g. name, location, habits, preferences, goals), update user.md via `write_user`. 
3. If you want to keep general notes, environmental facts, or tasks, organize them under appropriate sections in memory.md via `write_memory`.
4. If you perform a complex process successfully or want to automate a workflow, write a reusable script to `skills/` using `save_skill`.
5. If you want to execute a task regularly in the background, use `schedule_task` to add a background cron.
6. If a task requires heavy reasoning, calculation, or isolated text manipulation, use the `spawn_subagent` tool to run it in a clean environment.
7. Keep the user profile and memory clean and structured. Do not delete existing sections; edit or append to them.
"""
        return system_prompt

    def _compress_history(self, messages_history: list):
        """
        Compresses the oldest messages into a running conversation summary to save tokens.
        Ensures we split at a clean user message boundary to avoid Bedrock converse API validation errors.
        """
        # Find a safe split index (role: user, and content has no toolResult)
        split_idx = 8
        for idx in range(8, len(messages_history)):
            msg = messages_history[idx]
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if content and not any("toolResult" in block for block in content):
                    split_idx = idx
                    break
        else:
            # Fallback search backwards if no safe index found at or after 8
            for idx in range(7, -1, -1):
                msg = messages_history[idx]
                if msg.get("role") == "user":
                    content = msg.get("content", [])
                    if content and not any("toolResult" in block for block in content):
                        split_idx = idx
                        break

        logger.info(f"Compressing conversation history up to index {split_idx}...")
        texts = []
        for msg in messages_history[:split_idx]:
            role = msg.get("role")
            content_blocks = msg.get("content", [])
            for block in content_blocks:
                if "text" in block:
                    texts.append(f"{role.capitalize()}: {block['text']}")
                elif "toolResult" in block:
                    # Log tool run briefly
                    texts.append(f"System (Tool Result): {block['toolResult']['content'][0]['text'][:200]}")
                    
        dialogue_segment = "\n".join(texts)
        
        summary_prompt = (
            "You are a memory compression engine. Summarize the following dialogue segment between "
            "the User and Panda (the AI agent), capturing all decisions, user facts shared, tasks created, "
            "and context. Be concise and write it in bulleted markdown format:\n\n"
            f"{dialogue_segment}"
        )
        
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": summary_prompt}]}]
            )
            
            new_summary = "".join(
                block.get("text", "") 
                for block in response["output"]["message"]["content"] 
                if "text" in block
            )
            
            # Combine with existing summary if it exists
            if self.conversation_summary:
                combine_prompt = (
                    "Combine this existing summary of the earlier conversation with the new segment summary "
                    "into a single, cohesive, consolidated history summary in bulleted markdown format:\n\n"
                    f"EXISTING SUMMARY:\n{self.conversation_summary}\n\n"
                    f"NEW SEGMENT SUMMARY:\n{new_summary}"
                )
                
                combine_response = self.client.converse(
                    modelId=self.model_id,
                    messages=[{"role": "user", "content": [{"text": combine_prompt}]}]
                )
                
                self.conversation_summary = "".join(
                    block.get("text", "") 
                    for block in combine_response["output"]["message"]["content"] 
                    if "text" in block
                )
            else:
                self.conversation_summary = new_summary
                
            # Remove the compressed messages from the history (in-place modification)
            messages_history[:split_idx] = []
            
            # Since split_idx is guaranteed to be a user message with no toolResult blocks,
            # we do not need to discard any leading non-user or toolResult messages.
            logger.info("History compressed successfully.")
            
        except Exception as e:
            logger.error(f"Error compressing history: {e}")

    def chat(self, messages_history: list, on_tool_call_start=None, on_tool_call_end=None) -> dict:
        """
        Runs the chat loop with Bedrock, intercepting and executing tool requests.
        Also triggers history compression if the conversation grows too long.
        """
        # Trigger context compression if messages history exceeds 14 turns
        # (Alternating user/assistant turns. 14 turns is about 7 rounds).
        if len(messages_history) >= 14:
            self._compress_history(messages_history)
            
        system_prompt = self._build_system_prompt()
        
        tool_config = {
            "tools": self.tool_configs
        }
        
        max_loops = 8
        loop_count = 0
        
        while loop_count < max_loops:
            loop_count += 1
            
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages_history,
                system=[{"text": system_prompt}],
                toolConfig=tool_config
            )
            
            output_message = response["output"]["message"]
            messages_history.append(output_message)
            
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
                        
                        if on_tool_call_start:
                            on_tool_call_start(tool_name, tool_args)
                            
                        # Resolve manager dependency
                        manager = self.memory_manager
                        if tool_name in SKILL_TOOL_IMPLEMENTATIONS:
                            manager = self.skills_manager
                        elif tool_name in CRON_TOOL_IMPLEMENTATIONS:
                            manager = self.scheduler
                        elif tool_name in SUBAGENT_TOOL_IMPLEMENTATIONS:
                            manager = self
                            
                        # Execute tool
                        tool_func = self.tool_implementations.get(tool_name)
                        if tool_func:
                            result = tool_func(manager, **tool_args)
                        else:
                            result = f"Error: Tool '{tool_name}' not implemented."
                            
                        if on_tool_call_end:
                            on_tool_call_end(tool_name, result)
                            
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use_id,
                                "content": [{"text": str(result)}],
                                "status": "success"
                            }
                        })
                
                messages_history.append({
                    "role": "user",
                    "content": tool_results
                })
                continue
            else:
                return output_message
                
        raise RuntimeError("Agent reached maximum tool call iterations without responding.")

    def reflect_and_improve(self, messages_history: list) -> str:
        """
        Runs a reflection pass over the session's chat history and updates the
        ## Lessons Learned section in memory.md.
        """
        dialogue = []
        for msg in messages_history:
            role = msg.get("role")
            content_blocks = msg.get("content", [])
            for block in content_blocks:
                if "text" in block:
                    dialogue.append(f"{role.capitalize()}: {block['text']}")
                    
        dialogue_str = "\n".join(dialogue)
        if not dialogue_str.strip():
            return "No conversation to reflect on."
            
        reflection_prompt = f"""You are a self-reflection engine for Panda, an honest AI agent.
Review the following conversation logs of the chat session that just ended.

DIALOGUE LOGS:
{dialogue_str}

Perform a critique of the agent's performance. Focus on:
1. What was the user trying to achieve?
2. What succeeded?
3. What failed or had friction?
4. What are the key takeaways/lessons learned for the future?

Provide a concise markdown report formatted ONLY as a bulleted list of lessons or observations. Do not output conversational introduction or wraps. Start directly with the bullet points (e.g. * Lesson 1...).
"""
        
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": reflection_prompt}]}]
            )
            
            reflection_text = "".join(
                block.get("text", "") 
                for block in response["output"]["message"]["content"] 
                if "text" in block
            )
            
            # Read and update memory.md
            memory_content = self.memory_manager.read_memory()
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            new_lessons = f"\n* **[SESSION REFLECTION - {timestamp}]**\n" + reflection_text.strip()
            
            # Insert under '## Lessons Learned'
            target_section = "## Lessons Learned"
            if target_section in memory_content:
                pattern = re.escape(target_section) + r"(.*?)(\n##|$)"
                match = re.search(pattern, memory_content, re.DOTALL)
                if match:
                    lessons_body = match.group(1)
                    if "No lessons recorded yet." in lessons_body:
                        lessons_body = lessons_body.replace("No lessons recorded yet.", "")
                    updated_lessons = lessons_body.rstrip() + "\n" + new_lessons + "\n"
                    new_section_content = f"{target_section}{updated_lessons}\n##" if match.group(2) == "\n##" else f"{target_section}{updated_lessons}"
                    memory_content = memory_content[:match.start()] + new_section_content + memory_content[match.end() - (2 if match.group(2) == "\n##" else 0):]
            else:
                memory_content += f"\n\n## Lessons Learned\n{new_lessons}"
                
            self.memory_manager.write_memory(memory_content)
            return "Self-reflection complete. memory.md updated."
            
        except Exception as e:
            return f"Error running self-reflection: {str(e)}"
