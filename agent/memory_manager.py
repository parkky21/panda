import os

class MemoryManager:
    """
    Decoupled memory manager handling flat, structured memory files.
    Manages soul.md (read-only), user.md (read-write), and memory.md (read-write).
    """
    def __init__(self, memory_dir: str):
        self.memory_dir = os.path.abspath(memory_dir)
        os.makedirs(self.memory_dir, exist_ok=True)
        
        self.soul_path = os.path.join(self.memory_dir, "soul.md")
        self.user_path = os.path.join(self.memory_dir, "user.md")
        self.memory_path = os.path.join(self.memory_dir, "memory.md")

    def read_soul(self) -> str:
        """Reads the unchangeable soul/personality prompt."""
        if not os.path.exists(self.soul_path):
            raise FileNotFoundError(f"Soul file not found at {self.soul_path}")
        with open(self.soul_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_tools_description(self) -> str:
        """Reads the unchangeable tools description."""
        path = os.path.join(self.memory_dir, "tools.md")
        if not os.path.exists(path):
            return "# Tools\nNo custom tools documented."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def read_user(self) -> str:
        """Reads the structured user facts and preferences (user.md)."""
        if not os.path.exists(self.user_path):
            return "# User Profile\n\n## Personal Info\n* Name:\n\n## Preferences\n* Favorite Programming Language:\n\n## Communication Style\n*"
        with open(self.user_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_user(self, content: str) -> str:
        """Overwrites or updates the user profile (user.md)."""
        with open(self.user_path, "w", encoding="utf-8") as f:
            f.write(content)
        return "User profile updated successfully."

    def read_memory(self) -> str:
        """Reads the structured agent notes and environment state (memory.md)."""
        if not os.path.exists(self.memory_path):
            return "# Agent Memory\n\n## Environmental Facts\n*\n\n## Tasks & TODOs\n*\n\n## General Notes\n*"
        with open(self.memory_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_memory(self, content: str) -> str:
        """Overwrites or updates the agent memory (memory.md)."""
        with open(self.memory_path, "w", encoding="utf-8") as f:
            f.write(content)
        return "Agent memory updated successfully."
