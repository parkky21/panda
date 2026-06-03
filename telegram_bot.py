import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from agent.orchestrator import PandaOrchestrator
from agent.config import AgentConfig

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Dictionary to store chat histories by chat_id
chat_histories = {}
orchestrator = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets conversation and welcomes the user."""
    chat_id = update.effective_chat.id
    chat_histories[chat_id] = []
    
    welcome_text = (
        "🐼 *Panda's Bamboo Corner* 🐼\n\n"
        "Hey! I'm Panda, your warm and loyal companion. Ask me anything, tell me about your day, "
        "or let me help you build your projects!\n\n"
        "Use /reset to clear history, or /reflect to trigger a self-reflection summary."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets conversation history."""
    chat_id = update.effective_chat.id
    chat_histories[chat_id] = []
    await update.message.reply_text("🐼 Conversation history cleared!")

async def reflect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers self-reflection loop for the current conversation."""
    chat_id = update.effective_chat.id
    history = chat_histories.get(chat_id, [])
    
    if not history:
        await update.message.reply_text("🐼 Nothing to reflect on yet! Let's chat first.")
        return
        
    await update.message.reply_text("🐼 Reflecting on our conversation...")
    
    # Run reflection in a thread pool to avoid blocking the event loop
    report = await asyncio.to_thread(orchestrator.reflect_and_improve, history)
    await update.message.reply_text(f"✓ {report}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming text chats and routes them through the orchestrator."""
    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []
        
    history = chat_histories[chat_id]
    history.append({"role": "user", "content": [{"text": user_text}]})
    
    # Send typing status
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    loop = asyncio.get_running_loop()
    
    # Define non-blocking callbacks for tool run indicators
    def on_tool_call_start(tool_name, tool_args):
        args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
        asyncio.run_coroutine_threadsafe(
            update.message.reply_text(f"🔧 *Tool Start:* `{tool_name}({args_str})`", parse_mode="Markdown"),
            loop
        )
        
    def on_tool_call_end(tool_name, result):
        preview = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
        asyncio.run_coroutine_threadsafe(
            update.message.reply_text(f"✓ *Tool End:* `{tool_name}` finished.\nResult: `{preview}`", parse_mode="Markdown"),
            loop
        )
        
    try:
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
        
        # Reply to user
        await update.message.reply_text(text_response)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text(f"⚠️ An error occurred: {e}")

async def cron_loop_async(orchestrator_instance):
    """Runs background scheduler check every 10 seconds."""
    while True:
        try:
            await asyncio.to_thread(
                orchestrator_instance.scheduler.run_due_tasks,
                orchestrator_instance.skills_manager
            )
        except Exception as e:
            logger.error(f"Error in background cron loop: {e}")
        await asyncio.sleep(10)

def main():
    global orchestrator
    
    token = AgentConfig.get_telegram_token()
    if not token:
        print("[bold red]Error:[/bold red] TELEGRAM_BOT_TOKEN is not set in your .env file.", file=sys.stderr)
        print("Please create a bot via @BotFather and set the token to run the messaging gateway.", file=sys.stderr)
        sys.exit(1)
        
    memory_dir = "./memory"
    skills_dir = "./skills"
    
    # Initialize main orchestrator
    orchestrator = PandaOrchestrator(
        memory_dir=memory_dir,
        skills_dir=skills_dir
    )
    
    # Start Telegram Application
    application = ApplicationBuilder().token(token).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("reflect", reflect))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Get loop and run cron checker task
    loop = asyncio.get_event_loop()
    loop.create_task(cron_loop_async(orchestrator))
    
    # Start bot
    print("🐼 Starting Panda Telegram Bot Gateway...")
    application.run_polling()

if __name__ == '__main__':
    main()
