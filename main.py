import os
import sys
import time
import threading
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Load env variables before loading agent modules
load_dotenv()

from agent.orchestrator import PandaOrchestrator
from agent.config import AgentConfig

console = Console()

def run_cron_loop(orchestrator, stop_event):
    """
    Background daemon thread function that checks and executes
    due cron tasks every 10 seconds.
    """
    while not stop_event.is_set():
        try:
            # Execute due crons
            orchestrator.scheduler.run_due_tasks(orchestrator.skills_manager)
        except Exception as e:
            # Suppress errors to prevent thread crashing, but log to stderr
            print(f"\n[Cron Error]: {e}", file=sys.stderr)
        
        # Sleep in short increments to allow rapid shutdown response
        for _ in range(10):
            if stop_event.is_set():
                break
            time.sleep(1.0)

def main():
    memory_dir = "./memory"
    skills_dir = "./skills"
    model_id = AgentConfig.get_model_id()

    
    # Verify environment keys are set
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        console.print("[bold red]Error:[/bold red] AWS_BEARER_TOKEN_BEDROCK environment variable is not set in your .env file.")
        sys.exit(1)
        
    console.print(Panel.fit(
        f"[bold green]🐼 Welcome to Panda's bamboo corner! 🐼[/bold green]\n"
        f"I'm Panda, your persistent personal assistant.\n"
        f"Model: [cyan]{model_id}[/cyan]\n"
        f"Type [bold red]'quit'[/bold red] or [bold red]'exit'[/bold red] to end the chat and trigger reflection.",
        border_style="green"
    ))
    
    # Initialize orchestrator
    try:
        orchestrator = PandaOrchestrator(
            memory_dir=memory_dir,
            skills_dir=skills_dir,
            model_id=model_id
        )
    except Exception as e:
        console.print(f"[bold red]Failed to initialize Panda Orchestrator:[/bold red] {e}")
        sys.exit(1)
        
    messages_history = []
    
    # Start background scheduler thread
    stop_event = threading.Event()
    cron_thread = threading.Thread(
        target=run_cron_loop,
        args=(orchestrator, stop_event),
        daemon=True
    )
    cron_thread.start()
    
    # Tool callback handlers for real-time console reporting
    current_status = None
    
    def on_tool_call_start(tool_name, tool_args):
        nonlocal current_status
        args_str = ", ".join(f"{k}={v}" for k, v in tool_args.items())
        current_status = console.status(f"[bold yellow]🔧 Panda is running: [cyan]{tool_name}({args_str})[/cyan]...[/bold yellow]")
        current_status.start()
        
    def on_tool_call_end(tool_name, result):
        nonlocal current_status
        if current_status:
            current_status.stop()
            current_status = None
        # Format preview of result if it's long
        preview = str(result)[:80] + "..." if len(str(result)) > 80 else str(result)
        console.print(f"[dim yellow]✓ Tool [cyan]{tool_name}[/cyan] completed. Result: {preview}[/dim yellow]")
        
    session_ended = False
    try:
        while True:
            # Prompt the user
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if user_input.lower() in ["quit", "exit"]:
                break
                
            if not user_input.strip():
                continue
                
            # Append user message
            messages_history.append({"role": "user", "content": [{"text": user_input}]})
            
            # Show a thinking status while Bedrock generates response
            with console.status("[bold green]Panda is chewing some bamboo...[/bold green]", spinner="growVertical"):
                response = orchestrator.chat(
                    messages_history=messages_history,
                    on_tool_call_start=on_tool_call_start,
                    on_tool_call_end=on_tool_call_end
                )
                
            # Extract assistant's final response text
            content_blocks = response.get("content", [])
            text_response = "".join(block.get("text", "") for block in content_blocks if "text" in block)
            
            # Strip think tags to keep conversation clean
            import re
            text_response = re.sub(r"<think>.*?</think>", "", text_response, flags=re.DOTALL)
            text_response = re.sub(r"<think>.*", "", text_response, flags=re.DOTALL).strip()
            
            # Print response inside a panel
            console.print("\n")
            console.print(Panel(
                Markdown(text_response),
                title="[bold green]🐼 Panda[/bold green]",
                title_align="left",
                border_style="green"
            ))
            
    except KeyboardInterrupt:
        pass
    finally:
        session_ended = True
        console.print("\n[bold yellow]🚪 Closing conversation loop...[/bold yellow]")
        
        # Stop background crons
        stop_event.set()
        cron_thread.join(timeout=2.0)
        
        # Trigger Self-Reflection Loop
        if messages_history:
            console.print("[bold green]Panda is reflecting on our conversation...[/bold green]")
            with console.status("[bold green]Analyzing dialogue and extracting lessons...[/bold green]", spinner="dots"):
                report = orchestrator.reflect_and_improve(messages_history)
                console.print(f"[dim green]✓ {report}[/dim green]")
                
        console.print("[bold green]Panda:[/bold green] Catch you later! Stay true. 👋")

if __name__ == "__main__":
    main()
