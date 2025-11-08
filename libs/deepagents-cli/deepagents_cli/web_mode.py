
"""Handles the web development mode."""

import sys
import pychrome
from .config import console
from .tools import chrome_navigate, websocket_send_command

def setup_web_mode():
    """Checks for web mode dependencies and returns web-related tools."""
    console.print("Initializing web mode...")
    try:
        import pychrome
        import websockets
    except ImportError:
        console.print("[bold red]❌ Error:[/bold red] Missing web dependencies.")
        console.print("Please install them with:")
        console.print("  pip install 'deepagents-cli[web]'")
        sys.exit(1)

    # Check for Chrome connection
    try:
        browser = pychrome.Browser(url="http://127.0.0.1:9222")
        # Just testing connection, so we don't need to do anything with it.
    except pychrome.exceptions.ConnectionError:
        console.print("\n[yellow]⚠ Warning:[/yellow] Could not connect to Chrome's remote debugging port (9222).")
        console.print("The 'chrome_navigate' tool will not work until Chrome is started with the remote debugging flag.")
        console.print("Example:")
        console.print("  google-chrome --remote-debugging-port=9222")
        console.print("  chromium-browser --remote-debugging-port=9222")

    return [chrome_navigate, websocket_send_command]
