"""Lockout persistence using tmpfs.

Stores lockout state in /tmp so it is cleared on reboot.
"""

from __future__ import annotations

import time
from pathlib import Path

LOCKOUT_FILE = Path("/tmp/robco-greeter-lockout")


def is_locked_out() -> bool:
    """Check if a lockout state exists from a previous run."""
    return LOCKOUT_FILE.exists()


def set_lockout() -> None:
    """Set the lockout flag."""
    LOCKOUT_FILE.write_text(str(time.time()))


def clear_lockout() -> None:
    """Clear the lockout flag (normally done by reboot via tmpfs)."""
    if LOCKOUT_FILE.exists():
        LOCKOUT_FILE.unlink()
