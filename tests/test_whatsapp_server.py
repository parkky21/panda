import pytest
import json
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure environment variables are mocked before imports
@pytest.fixture(autouse=True)
def setup_mock_env(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "mock_bedrock_token")
    monkeypatch.setenv("MODEL_ID", "mock-model")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("WHATSAPP_TOKEN", "mock_wa_token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "mock_wa_phone_id")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify_token_123")

from whatsapp_server import app, startup_event, send_whatsapp_message, process_webhook_payload
import whatsapp_server

@pytest.fixture
def client(temp_memory_dir, temp_skills_dir):
    # Initialize the orchestrator inside the server before running tests
    # Mock loop and startup
    with patch('boto3.client'):
        with TestClient(app) as test_client:
            yield test_client

def test_webhook_verification_success(client):
    res = client.get("/webhook?hub.mode=subscribe&hub.verify_token=verify_token_123&hub.challenge=challenge_token_abc")
    assert res.status_code == 200
    assert res.text == "challenge_token_abc"

def test_webhook_verification_mismatch(client):
    res = client.get("/webhook?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=challenge")
    assert res.status_code == 403
    assert "Verification token mismatch" in res.json()["detail"]

def test_webhook_verification_missing_params(client):
    res = client.get("/webhook")
    assert res.status_code == 403

def test_webhook_post_acknowledgement(client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.ID",
                                    "text": {"body": "Hello Panda!"}
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    # POST webhook should return 200 immediately
    res = client.post("/webhook", json=payload)
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

@pytest.mark.anyio
@patch('whatsapp_server.send_whatsapp_message')
@patch('asyncio.to_thread')
async def test_process_webhook_payload(mock_to_thread, mock_send_wa, temp_memory_dir, temp_skills_dir):
    # Setup mock event loop reference in module
    whatsapp_server.loop = asyncio.get_running_loop()
    
    # Initialize mock orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.chat.return_value = {
        "content": [{"text": "Panda reply text!"}]
    }
    whatsapp_server.orchestrator = mock_orchestrator
    
    # Mock to_thread execution
    mock_to_thread.return_value = mock_orchestrator.chat.return_value
    
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "text": {"body": "Hello"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    await process_webhook_payload(payload)
    
    # Verify orchestrator was triggered
    mock_to_thread.assert_called_once()
    # Verify response sent back
    mock_send_wa.assert_called_with("15551234567", "Panda reply text!")

@pytest.mark.anyio
@patch('httpx.AsyncClient')
async def test_send_whatsapp_message(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response
    
    await send_whatsapp_message("15551234567", "hello user")
    
    # Verify POST request was dispatched to Meta Cloud API
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert "https://graph.facebook.com/v25.0/mock_wa_phone_id/messages" in args[0]
    assert kwargs["json"]["to"] == "15551234567"
    assert kwargs["json"]["text"]["body"] == "hello user"
