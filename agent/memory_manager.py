import os
import re

class MemoryManager:
    """
    Decoupled memory manager handling local markdown memory files.
    Ensures safe operations, prevents editing of read-only files (soul, tools),
    and manages links between memory nodes.
    """
    def __init__(self, memory_dir: str):
        self.memory_dir = os.path.abspath(memory_dir)
        self.nodes_dir = os.path.join(self.memory_dir, "nodes")
        os.makedirs(self.nodes_dir, exist_ok=True)
        
        # Read-only files
        self.readonly_files = {"soul.md", "tools.md"}

    def _resolve_path(self, node_name: str) -> str:
        """
        Resolves a node name to an absolute file path.
        Standardizes node names to lowercase and appends .md extension if missing.
        """
        if not node_name.endswith(".md"):
            node_name += ".md"
            
        # Check if it's a root level file (like LongTermMemory.md or user_profile.md)
        if node_name.lower() in ["longtermmemory.md", "user_profile.md"]:
            target_path = os.path.join(self.memory_dir, node_name)
        else:
            target_path = os.path.join(self.nodes_dir, node_name)
            
        target_path = os.path.abspath(target_path)
        
        # Security check: Ensure the path is within the memory directory
        if not target_path.startswith(self.memory_dir):
            raise PermissionError("Access denied: File path is outside the memory directory.")
            
        return target_path

    def read_soul(self) -> str:
        """Reads the unchangeable soul prompt."""
        path = os.path.join(self.memory_dir, "soul.md")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def read_tools_description(self) -> str:
        """Reads the unchangeable tools description."""
        path = os.path.join(self.memory_dir, "tools.md")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def read_user_profile(self) -> str:
        """Reads the user profile (Memory 5)."""
        path = os.path.join(self.memory_dir, "user_profile.md")
        if not os.path.exists(path):
            return "# User Profile\n\nNo details recorded yet."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def update_user_profile(self, new_content: str) -> str:
        """Rewrites or updates the user profile."""
        path = os.path.join(self.memory_dir, "user_profile.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return "User profile updated successfully."

    def read_node(self, node_name: str) -> str:
        """Reads a specific memory node in the long-term memory graph."""
        file_name = os.path.basename(node_name)
        if file_name in self.readonly_files:
            raise PermissionError(f"Access denied: {file_name} is read-only.")
            
        path = self._resolve_path(node_name)
        if not os.path.exists(path):
            return f"Error: Memory node '{node_name}' does not exist."
            
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_node(self, node_name: str, content: str) -> str:
        """Writes a memory node, creating it if it doesn't exist."""
        file_name = os.path.basename(node_name)
        if file_name in self.readonly_files:
            raise PermissionError(f"Access denied: {file_name} is read-only.")
            
        path = self._resolve_path(node_name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Memory node '{node_name}' written successfully."

    def link_nodes(self, parent_node: str, child_node: str, description: str) -> str:
        """
        Links a child node to a parent node by appending a markdown link
        in the parent node's file.
        """
        parent_path = self._resolve_path(parent_node)
        if not os.path.exists(parent_path):
            return f"Error: Parent node '{parent_node}' does not exist."
            
        # Verify child path can be resolved safely
        child_path = self._resolve_path(child_node)
        
        # Determine relative link path from parent
        # Root files are in memory_dir, nodes are in nodes_dir
        parent_basename = os.path.basename(parent_path).lower()
        if parent_basename in ["longtermmemory.md", "user_profile.md"]:
            relative_link = f"nodes/{os.path.basename(child_path)}"
        else:
            relative_link = os.path.basename(child_path)
            
        link_markdown = f"\n* [{description}]({relative_link})"
        
        with open(parent_path, "a", encoding="utf-8") as f:
            f.write(link_markdown)
            
        return f"Successfully linked '{child_node}' to '{parent_node}'."
