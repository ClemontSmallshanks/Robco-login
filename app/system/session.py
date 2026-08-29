"""Session management (stub for development mode)."""

from __future__ import annotations

import sys


def start_session(username: str, development_mode: bool = True) -> None:
    """Start a user desktop session after successful authentication."""
    if development_mode:
        print(f"DEVELOPMENT MODE: Session start for user '{username}'")
        sys.exit(0)
    # In production with greetd, the GreetdAuthenticator handles session launch
    # via IPC. greetd will tear down the greeter environment automatically.
    pass
