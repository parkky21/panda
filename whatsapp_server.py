import os
import sys
import logging
import asyncio
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from dotenv import load_dotenv

# Load environment
load_dotenv()

from agent.orchestrator import PandaOrchestrator
from agent.config import AgentConfig

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Panda WhatsApp Gateway")

# Shared history memory cache by phone number
chat_histories = {}
orchestrator = None
loop = None

@app.on_event("startup")
async def startup_event():
    """Initializes the orchestrator and starts the background cron loop."""
    global orchestrator, loop
    loop = asyncio.get_running_loop()
    
    memory_dir = "./memory"
    skills_dir = "./skills"
    
    # Initialize orchestrator
    orchestrator = PandaOrchestrator(
        memory_dir=memory_dir,
        skills_dir=skills_dir
    )
    
    # Start background scheduler check
    asyncio.create_task(cron_loop_async(orchestrator))
    logger.info("Panda WhatsApp Gateway initialized and background crons loop started.")

async def cron_loop_async(orchestrator_instance):
    """Periodically executes scheduled tasks in the background."""
    while True:
        try:
            await asyncio.to_thread(
                orchestrator_instance.scheduler.run_due_tasks,
                orchestrator_instance.skills_manager
            )
        except Exception as e:
            logger.error(f"Error in background cron loop: {e}")
        await asyncio.sleep(10)

async def send_whatsapp_message(to: str, text: str):
    """Sends a text message response back to the user via Meta Graph API."""
    token = AgentConfig.get_whatsapp_token()
    phone_id = AgentConfig.get_whatsapp_phone_number_id()
    
    if not token or not phone_id:
        logger.warning(f"Skipped sending WhatsApp message. Credentials not set. Message: {text}")
        return
        
    url = f"https://graph.facebook.com/v25.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"Meta API failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error calling Meta Graph API: {e}")

@app.get("/webhook")
def verify_webhook(request: Request):
    """Handles the Meta Webhook Verification GET Handshake challenge."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    expected_token = AgentConfig.get_whatsapp_verify_token()
    
    if mode == "subscribe" and token == expected_token:
        logger.info("Webhook verified successfully.")
        return Response(content=challenge, media_type="text/plain")
        
    logger.warning(f"Webhook verification failed. Token mismatch. Expected: {expected_token}, Got: {token}")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives POST updates (messages and statuses) from Meta."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    # Standard acknowledge to Meta (must respond HTTP 200 immediately)
    background_tasks.add_task(process_webhook_payload, body)
    return {"status": "ok"}

async def process_webhook_payload(body: dict):
    """Parses message body and triggers orchestrator response in background."""
    try:
        # Check if entry, changes, and value exist
        entry = body.get("entry", [])
        if not entry:
            return
        changes = entry[0].get("changes", [])
        if not changes:
            return
        value = changes[0].get("value", {})
        
        # Check if messages exist (Meta sends status updates without messages key)
        messages = value.get("messages", [])
        if not messages:
            return
            
        msg = messages[0]
        sender = msg.get("from")
        text = msg.get("text", {}).get("body", "")
        
        if not sender or not text:
            return
            
        logger.info(f"Received WhatsApp message from {sender}: {text}")
        
        # Retrieve or initialize chat history
        if sender not in chat_histories:
            chat_histories[sender] = []
            
        history = chat_histories[sender]
        history.append({"role": "user", "content": [{"text": text}]})
        
        # Define tool callbacks to notify user on WhatsApp during tool execution
        def on_tool_call_start(tool_name, tool_args):
            args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
            asyncio.run_coroutine_threadsafe(
                send_whatsapp_message(sender, f"🔧 Panda is running: {tool_name}({args_str})..."),
                loop
            )
            
        def on_tool_call_end(tool_name, result):
            preview = str(result)[:80] + "..." if len(str(result)) > 80 else str(result)
            asyncio.run_coroutine_threadsafe(
                send_whatsapp_message(sender, f"✓ Tool finished: {tool_name}. Result:\n{preview}"),
                loop
            )
            
        # Run orchestrator chat loop in a thread pool
        response = await asyncio.to_thread(
            orchestrator.chat,
            history,
            on_tool_call_start,
            on_tool_call_end
        )
        
        # Extract assistant response text
        content_blocks = response.get("content", [])
        text_response = "".join(block.get("text", "") for block in content_blocks if "text" in block)
        
        # Strip think tags to keep conversation clean
        import re
        text_response = re.sub(r"<think>.*?</think>", "", text_response, flags=re.DOTALL)
        text_response = re.sub(r"<think>.*", "", text_response, flags=re.DOTALL).strip()
        
        # Send reply back to user
        await send_whatsapp_message(sender, text_response)
        
    except Exception as e:
        logger.error(f"Error processing webhook payload: {e}")
