import os
import pytest
import shutil

@pytest.fixture
def mock_env(monkeypatch):
    """Mocks default AWS and Telegram environment variables."""
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "mock_bedrock_token")
    monkeypatch.setenv("MODEL_ID", "mock-model-id")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock_telegram_token")

@pytest.fixture
def temp_memory_dir(tmp_path):
    """Creates a temporary memory folder with default soul, user, and memory files."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    
    # Write mock soul.md
    soul_file = memory_dir / "soul.md"
    soul_file.write_text("# Soul\nYou are a mock agent named Panda.", encoding="utf-8")
    
    # Write mock user.md
    user_file = memory_dir / "user.md"
    user_file.write_text("# User Profile\n\n## Personal Info\n* Name: Parth\n\n## Preferences\n* Favorite Programming Language: Python\n\n## Interests\n* AI\n\n## Goals\n*\n\n## Communication Style\n*", encoding="utf-8")
    
    # Write mock memory.md
    mem_file = memory_dir / "memory.md"
    mem_file.write_text("# Agent Memory\n\n## Environmental Facts\n* No facts.\n\n## Tasks & TODOs\n* No tasks.\n\n## General Notes\n* No notes.\n\n## Lessons Learned\n* No lessons.", encoding="utf-8")
    
    # Write mock tools.md
    tools_file = memory_dir / "tools.md"
    tools_file.write_text("# Tools\n* mock_tool", encoding="utf-8")
    
    return str(memory_dir)

@pytest.fixture
def temp_skills_dir(tmp_path):
    """Creates a temporary skills directory."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return str(skills_dir)
