import os
from agent.config import AgentConfig

def test_config_defaults(monkeypatch):
    """Test default config values when environment variables are not set."""
    monkeypatch.delenv("MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    
    assert AgentConfig.get_model_id() == "moonshotai.kimi-k2.5"
    assert AgentConfig.get_aws_region() == "us-east-1"
    assert AgentConfig.get_telegram_token() == ""
    assert AgentConfig.get_discord_token() == ""

def test_config_custom(mock_env, monkeypatch):
    """Test custom config values when environment variables are set."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock_discord_token")
    assert AgentConfig.get_model_id() == "mock-model-id"
    assert AgentConfig.get_aws_region() == "us-east-1"
    assert AgentConfig.get_telegram_token() == "mock_telegram_token"
    assert AgentConfig.get_discord_token() == "mock_discord_token"
