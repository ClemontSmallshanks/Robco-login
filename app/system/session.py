"""Session management (stub for development mode)."""

from __future__ import annotations

import sys


def start_session(username: str, development_mode: bool = True) -> None:
    """Start a user desktop session after successful authentication."""
    import time
    print(f"[DIAG-TIME] {time.perf_counter():.6f} [13] session.py: start_session({username}, dev={development_mode}) called", flush=True)
    if development_mode:
        print(f"DEVELOPMENT MODE: Session start for user '{username}'")
        sys.exit(0)
    # In production with greetd, the GreetdAuthenticator handles session launch
    # via IPC. greetd will tear down the greeter environment automatically.
    print(f"[DIAG-TIME] {time.perf_counter():.6f} [14] session.py: returning without doing anything (production mode)", flush=True)
    pass
