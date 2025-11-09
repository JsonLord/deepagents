"""Tests for the main CLI entry point."""
from unittest.mock import patch

from deepagents_cli import main

def test_cli_main_starts_server():
    """Test that cli_main calls start_server."""
    with patch("deepagents_cli.main.start_server") as mock_start_server:
        with patch("deepagents_cli.main.check_cli_dependencies"):
            with patch("deepagents_cli.main.parse_args"):
                with patch("asyncio.run"):
                    main.cli_main()
                    mock_start_server.assert_called_once_with()
