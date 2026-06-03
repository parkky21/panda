import os
import pytest
from agent.memory_manager import MemoryManager

def test_read_soul(temp_memory_dir):
    manager = MemoryManager(temp_memory_dir)
    soul = manager.read_soul()
    assert "You are a mock agent named Panda" in soul

def test_read_tools_description(temp_memory_dir):
    manager = MemoryManager(temp_memory_dir)
    tools = manager.read_tools_description()
    assert "mock_tool" in tools

def test_read_user_profile(temp_memory_dir):
    manager = MemoryManager(temp_memory_dir)
    user = manager.read_user()
    assert "Name: Parth" in user
    assert "Favorite Programming Language: Python" in user

def test_write_user_profile(temp_memory_dir):
    manager = MemoryManager(temp_memory_dir)
    res = manager.write_user("# User Profile\n\n* Name: John")
    assert "updated successfully" in res
    assert "Name: John" in manager.read_user()

def test_read_memory_state(temp_memory_dir):
    manager = MemoryManager(temp_memory_dir)
    memory = manager.read_memory()
    assert "Environmental Facts" in memory
    assert "Tasks & TODOs" in memory

def test_write_memory_state(temp_memory_dir):
    manager = MemoryManager(temp_memory_dir)
    res = manager.write_memory("# Agent Memory\n\n* Task: code tests")
    assert "updated successfully" in res
    assert "Task: code tests" in manager.read_memory()

def test_missing_files_handling(tmp_path):
    # Test fallback defaults when files don't exist
    empty_dir = tmp_path / "empty"
    manager = MemoryManager(str(empty_dir))
    
    with pytest.raises(FileNotFoundError):
        manager.read_soul()
        
    assert "No custom tools" in manager.read_tools_description()
    assert "User Profile" in manager.read_user()
    assert "Agent Memory" in manager.read_memory()
