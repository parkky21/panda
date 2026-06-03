import os
import sys
import boto3
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv()

console = Console()

def main():
    # Initialize the Bedrock client
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    model_id = 'moonshotai.kimi-k2.5'
    
    console.print(Panel.fit(
        f"[bold blue]🤖 Welcome to the AI Agent[/bold blue]\n"
        f"Model: [cyan]{model_id}[/cyan]\n"
        f"Type [bold red]'quit'[/bold red] or [bold red]'exit'[/bold red] to end the conversation.", 
        border_style="blue"
    ))
    
    messages = []
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if user_input.lower() in ['quit', 'exit']:
                console.print("\n[bold red]Goodbye![/bold red] 👋")
                break
            
            if not user_input.strip():
                continue
                
            # Append user message
            messages.append({"role": "user", "content": [{"text": user_input}]})
            
            # Show a thinking spinner while waiting for response
            with console.status("[bold cyan]Agent is thinking...", spinner="dots"):
                response = client.converse(
                    modelId=model_id,
                    messages=messages
                )
            
            # Extract and display the response
            agent_message = response['output']['message']
            content_blocks = agent_message.get('content', [])
            text_response = "".join(block.get('text', '') for block in content_blocks)
            
            # Save assistant response to conversation history
            messages.append({"role": "assistant", "content": [{"text": text_response}]})
            
            # Print the markdown response in a nice panel
            console.print("\n")
            console.print(Panel(
                Markdown(text_response), 
                title="[bold magenta]Agent[/bold magenta]", 
                title_align="left", 
                border_style="magenta"
            ))
            
        except KeyboardInterrupt:
            console.print("\n[bold red]Goodbye![/bold red] 👋")
            break
        except Exception as e:
            console.print(f"\n[bold red]An error occurred:[/bold red] {e}")

if __name__ == "__main__":
    main()
