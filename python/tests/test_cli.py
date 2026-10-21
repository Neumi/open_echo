"""Tests for the CLI argument parser."""

import sys
from unittest.mock import patch

import pytest


class TestCLIParser:
    def test_desktop_subcommand_default_server_url(self):
        with (
            patch.object(sys, "argv", ["openecho", "desktop"]),
            patch("open_echo.cli.run_desktop") as mock_run,
        ):
            from open_echo.cli import main

            main()
            mock_run.assert_called_once_with(server_url="http://localhost:8000")

    def test_desktop_subcommand_custom_server_url(self):
        with (
            patch.object(
                sys,
                "argv",
                ["openecho", "desktop", "--server-url", "http://myhost:9000"],
            ),
            patch("open_echo.cli.run_desktop") as mock_run,
        ):
            from open_echo.cli import main

            main()
            mock_run.assert_called_once_with(server_url="http://myhost:9000")

    def test_web_subcommand(self):
        with (
            patch.object(sys, "argv", ["openecho", "web"]),
            patch("open_echo.cli.run_web") as mock_run,
        ):
            from open_echo.cli import main

            main()
            mock_run.assert_called_once()

    def test_missing_subcommand_exits(self):
        with patch.object(sys, "argv", ["openecho"]), pytest.raises(SystemExit):
            from open_echo.cli import main

            main()

    def test_invalid_subcommand_exits(self):
        with (
            patch.object(sys, "argv", ["openecho", "nonexistent"]),
            pytest.raises(SystemExit),
        ):
            from open_echo.cli import main

            main()
