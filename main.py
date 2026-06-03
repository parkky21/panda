import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

# Load env variables before loading agent modules
load_dotenv()

from agent.orchestrator import PandaOrchestrator

console = Console()

def main():
    memory_dir = "./memory"
    model_id = "moonshotai.kimi-k2.5"
    
    # Verify environment keys are set
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        console.print("[bold red]Error:[/bold red] AWS_BEARER_TOKEN_BEDROCK environment variable is not set in your .env file.")
        sys.exit(1)
        
    console.print(Panel.fit(
        f"[bold green]🐼 Welcome to Panda's bamboo corner! 🐼[/bold green]\n"
        f"I'm Panda. I'm playful, optimistic, and I'll tell you the raw truth.\n"
        f"Model: [cyan]{model_id}[/cyan]\n"
        f"Type [bold red]'quit'[/bold red] or [bold red]'exit'[/bold red] to end the chat.",
        border_style="green"
    ))
    
    # Initialize orchestrator
    try:
        orchestrator = PandaOrchestrator(memory_dir=memory_dir, model_id=model_id)
    except Exception as e:
        console.print(f"[bold red]Failed to initialize Panda Orchestrator:[/bold red] {e}")
        sys.exit(1)
        
    messages_history = []
    
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
        console.print(f"[dim yellow]✓ Tool [cyan]{tool_name}[/cyan] completed.[/dim yellow]")
        
    while True:
        try:
            # Prompt the user
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if user_input.lower() in ["quit", "exit"]:
                console.print("\n[bold green]Panda:[/bold green] Catch you later! Stay true. 👋")
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
            
            # Print response inside a panel
            console.print("\n")
            console.print(Panel(
                Markdown(text_response),
                title="[bold green]🐼 Panda[/bold green]",
                title_align="left",
                border_style="green"
            ))
            
        except KeyboardInterrupt:
            console.print("\n[bold green]Panda:[/bold green] Bye! 👋")
            break
        except Exception as e:
            # Stop spinner if active
            if current_status:
                current_status.stop()
                current_status = None
            console.print(f"\n[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
