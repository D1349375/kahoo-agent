#!/usr/bin/env python3
"""
Entrypoint for kahoo-agent CLI.
"""

import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from kahoo_agent.cli import cli

if __name__ == "__main__":
    cli()
