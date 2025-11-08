
"""Handles the app development mode."""

import sys
from .config import console
from .tools import appium_command

def setup_app_mode():
    """Checks for app mode dependencies and returns app-related tools."""
    console.print("Initializing app mode...")
    try:
        import appium
    except ImportError:
        console.print("[bold red]❌ Error:[/bold red] Missing app dependencies.")
        console.print("Please install them with:")
        console.print("  pip install 'deepagents-cli[app]'")
        sys.exit(1)

    # Note: We don't check for Appium server connection here
    # because it's project-specific and better handled within the tool itself.

    return [appium_command]
