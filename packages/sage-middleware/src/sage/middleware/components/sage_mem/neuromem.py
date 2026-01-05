"""
Placeholder module for NeuroMem extension.

This module raises an error when imported if NeuroMem is not installed.
The actual NeuroMem package provides the real implementation via namespace packages.
"""

import sys

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
RESET = "\033[0m"

error_message = (
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"  {RED}{BOLD}NeuroMem Extension Not Installed{RESET}\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"NeuroMem is an optional extension for SAGE Middleware.\n"
    f"\n"
    f"To install NeuroMem:\n"
    f"  {GREEN}pip install isage-neuromem{RESET}\n"
    f"\n"
    f"Or install middleware with neuromem support:\n"
    f"  {GREEN}pip install isage-middleware[neuromem]{RESET}\n"
)

# Print to stderr and exit without traceback
sys.stderr.write(error_message)
sys.stderr.flush()
sys.exit(1)
