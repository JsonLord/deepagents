"""Main entry point and CLI loop for deepagents."""

import argparse
import asyncio
import sys
import subprocess
import os
from pathlib import Path

from .agent import create_agent_with_config, list_agents, reset_agent
from .app_mode import setup_app_mode
from .commands import execute_bash_command, handle_command
from .web_mode import setup_web_mode
from .config import COLORS, DEEP_AGENTS_ASCII, SessionState, console, create_model
from .execution import execute_task
from .input import create_prompt_session
from .tools import http_request, tavily_client, web_search
from .ui import TokenTracker, show_help


class Tee:
    """A file-like object that writes to multiple files."""

    def __init__(self, *files):
        self.files = files
        self._primary_stream = files[0]

    def write(self, obj):
        """Write to all files."""
        for f in self.files:
            f.write(obj)
            f.flush()  # Ensure it's written immediately

    def flush(self):
        """Flush all files."""
        for f in self.files:
            f.flush()

    def __getattr__(self, name):
        """Delegate attribute access to the primary stream."""
        return getattr(self._primary_stream, name)


def get_log_filename(agent_name: str) -> Path:
    """Generate a unique log filename."""
    i = 1
    while True:
        filename = Path.cwd() / f"conversation_with_{agent_name}_{i}.txt"
        if not filename.exists():
            return filename
        i += 1


def is_server_running(server_path):
    """Check if the mcp-rest-api server is running."""
    try:
        result = subprocess.run([os.path.join(server_path, "mcp_server"), "status"], capture_output=True, text=True, check=True)
        return "is running" in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_server():
    """Start the mcp-rest-api server if it's not already running."""
    server_path = Path(__file__).parent / "bin"
    if not is_server_running(server_path):
        console.print("[yellow]Starting mcp-rest-api server...[/yellow]")
        subprocess.Popen([os.path.join(server_path, "mcp_server"), "start"])
        console.print("[green]Server started.[/green]")


def check_cli_dependencies():
    """Check if CLI optional dependencies are installed."""
    missing = []

    try:
        import rich
    except ImportError:
        missing.append("rich")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    try:
        import dotenv
    except ImportError:
        missing.append("python-dotenv")

    try:
        import tavily
    except ImportError:
        missing.append("tavily-python")

    try:
        import prompt_toolkit
    except ImportError:
        missing.append("prompt-toolkit")

    if missing:
        print("\n❌ Missing required CLI dependencies!")
        print("\nThe following packages are required to use the deepagents CLI:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install them with:")
        print("  pip install deepagents[cli]")
        print("\nOr install all dependencies:")
        print("  pip install 'deepagents[cli]'")
        sys.exit(1)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DeepAgents - AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all available agents")

    # Help command
    subparsers.add_parser("help", help="Show help information")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset an agent")
    reset_parser.add_argument("--agent", required=True, help="Name of agent to reset")
    reset_parser.add_argument(
        "--target", dest="source_agent", help="Copy prompt from another agent"
    )

    # Default interactive mode
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for separate memory stores (default: agent).",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting (disables human-in-the-loop)",
    )
    parser.add_argument(
        "--think",
        action="store_true",
        help="Print reasoning for each step.",
    )
    parser.add_argument(
        "--log-file",
        action="store_true",
        help="Save the conversation to a file.",
    )
    parser.add_argument(
        "--mode",
        choices=["app", "web"],
        help="Set the development mode to either 'app' or 'web'.",
    )

    return parser.parse_args()


async def simple_cli(agent, assistant_id: str | None, session_state, baseline_tokens: int = 0):
    """Main CLI loop."""
    console.clear()
    console.print(DEEP_AGENTS_ASCII, style=f"bold {COLORS['primary']}")
    console.print()

    if tavily_client is None:
        console.print(
            "[yellow]⚠ Web search disabled:[/yellow] TAVILY_API_KEY not found.",
            style=COLORS["dim"],
        )
        console.print("  To enable web search, set your Tavily API key:", style=COLORS["dim"])
        console.print("    export TAVILY_API_KEY=your_api_key_here", style=COLORS["dim"])
        console.print(
            "  Or add it to your .env file. Get your key at: https://tavily.com",
            style=COLORS["dim"],
        )
        console.print()

    console.print("... Ready to code! What would you like to build?", style=COLORS["agent"])
    console.print(f"  [dim]Working directory: {Path.cwd()}[/dim]")
    console.print()

    if session_state.auto_approve:
        console.print(
            "  [yellow]⚡ Auto-approve: ON[/yellow] [dim](tools run without confirmation)[/dim]"
        )
        console.print()

    console.print(
        "  Tips: Enter to submit, Alt+Enter for newline, Ctrl+E for editor, Ctrl+T to toggle auto-approve, Ctrl+C to interrupt",
        style=f"dim {COLORS['dim']}",
    )
    console.print()

    # Create prompt session and token tracker
    session = create_prompt_session(assistant_id, session_state)
    token_tracker = TokenTracker()
    token_tracker.set_baseline(baseline_tokens)

    while True:
        try:
            user_input = await session.prompt_async()
            user_input = user_input.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            # Ctrl+C at prompt - exit the program
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        if not user_input:
            continue

        # Check for slash commands first
        if user_input.startswith("/"):
            result = handle_command(user_input, agent, token_tracker)
            if result == "exit":
                console.print("\nGoodbye!", style=COLORS["primary"])
                break
            if result:
                # Command was handled, continue to next input
                continue

        # Check for bash commands (!)
        if user_input.startswith("!"):
            execute_bash_command(user_input)
            continue

        # Handle regular quit keywords
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("\nGoodbye!", style=COLORS["primary"])
            break

        execute_task(user_input, agent, assistant_id, session_state, token_tracker)


async def main(assistant_id: str, session_state, mode: str = None):
    """Main entry point."""
    # Create the model (checks API keys)
    model = create_model()

    # Create agent with conditional tools
    tools = [http_request]
    if tavily_client is not None:
        tools.append(web_search)

    if mode == "app":
        tools.extend(setup_app_mode())
    elif mode == "web":
        tools.extend(setup_web_mode())

    agent = create_agent_with_config(model, assistant_id, tools)

    # Calculate baseline token count for accurate token tracking
    from .agent import get_system_prompt
    from .token_utils import calculate_baseline_tokens

    agent_dir = Path.home() / ".deepagents" / assistant_id
    system_prompt = get_system_prompt()
    baseline_tokens = calculate_baseline_tokens(model, agent_dir, system_prompt)

    try:
        await simple_cli(agent, assistant_id, session_state, baseline_tokens)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}\n")


def cli_main():
    """Entry point for console script."""
    # Start the mcp-rest-api server
    start_server()

    # Check dependencies first
    check_cli_dependencies()

    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        elif args.command == "list":
            list_agents()
        elif args.command == "reset":
            reset_agent(args.agent, args.source_agent)
        else:
            # Create session state from args
            session_state = SessionState(auto_approve=args.auto_approve, think=args.think)
            if args.mode == "app":
                setup_app_mode()
            elif args.mode == "web":
                setup_web_mode()

            if args.log_file:
                log_filename = get_log_filename(args.agent)
                with open(log_filename, "w") as f:
                    original_stdout = sys.stdout
                    sys.stdout = Tee(sys.stdout, f)
                    try:
                        # API key validation happens in create_model()
                        asyncio.run(main(args.agent, session_state, args.mode))
                    finally:
                        sys.stdout = original_stdout
            else:
                # API key validation happens in create_model()
                asyncio.run(main(args.agent, session_state, args.mode))
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C - suppress ugly traceback
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
