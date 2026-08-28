"""System power actions (stub for development mode)."""

from __future__ import annotations

import subprocess
import sys


def shutdown(development_mode: bool = True) -> None:
    """Perform system shutdown."""
    if development_mode:
        print("DEVELOPMENT MODE: System shutdown requested")
        sys.exit(0)
    subprocess.run(["systemctl", "poweroff"], check=True)


def restart(development_mode: bool = True) -> None:
    """Perform system reboot."""
    if development_mode:
        print("DEVELOPMENT MODE: System restart requested")
        sys.exit(0)
    subprocess.run(["systemctl", "reboot"], check=True)
