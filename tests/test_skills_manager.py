import os
import pytest
from unittest.mock import patch
from agent.skills_manager import SkillsManager

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("AUTO_APPROVE_SKILLS", raising=False)

def test_save_and_list_skills(temp_skills_dir):
    manager = SkillsManager(temp_skills_dir)
    
    # Save a python skill
    res1 = manager.save_skill(
        name="test_py_skill",
        code="print('Hello Python')",
        description="A simple python greeting skill"
    )
    assert "Successfully saved skill" in res1
    
    # Save a bash skill
    res2 = manager.save_skill(
        name="test_sh_skill",
        code="#!/bin/bash\necho 'Hello Bash'",
        description="A simple bash greeting skill"
    )
    assert "Successfully saved skill" in res2
    
    # List skills and verify files exist
    skills = manager.list_skills()
    assert "test_py_skill" in skills
    assert "test_sh_skill" in skills
    assert skills["test_py_skill"]["type"] == "python"
    assert skills["test_sh_skill"]["type"] == "bash"
    
    assert os.path.exists(os.path.join(temp_skills_dir, "test_py_skill.py"))
    assert os.path.exists(os.path.join(temp_skills_dir, "test_sh_skill.sh"))

def test_invalid_skill_name(temp_skills_dir):
    manager = SkillsManager(temp_skills_dir)
    res = manager.save_skill(
        name="../../../bad_path",
        code="print('evil')",
        description="attempting directory traversal"
    )
    assert "Error: Invalid skill name" in res

@patch('builtins.input', return_value='y')
def test_run_skill_approved(mock_input, temp_skills_dir):
    manager = SkillsManager(temp_skills_dir)
    
    # Save python script
    code = "import sys; print(f'Args received: {sys.argv[1:]}')"
    manager.save_skill("test_run", code, "prints args")
    
    # Run and verify stdout
    res = manager.run_skill("test_run", ["hello", "world"])
    assert "executed successfully" in res
    assert "Args received: ['hello', 'world']" in res

@patch('builtins.input', return_value='n')
def test_run_skill_denied(mock_input, temp_skills_dir):
    manager = SkillsManager(temp_skills_dir)
    manager.save_skill("test_run", "print('test')", "prints test")
    
    # Run and verify denied
    res = manager.run_skill("test_run")
    assert "User denied permission" in res

def test_run_nonexistent_skill(temp_skills_dir):
    manager = SkillsManager(temp_skills_dir)
    res = manager.run_skill("missing")
    assert "not found" in res

def test_run_skill_auto_approved(temp_skills_dir, monkeypatch):
    monkeypatch.setenv("AUTO_APPROVE_SKILLS", "true")
    manager = SkillsManager(temp_skills_dir)
    manager.save_skill("test_auto", "print('auto')", "auto approves execution")
    res = manager.run_skill("test_auto")
    assert "executed successfully" in res
