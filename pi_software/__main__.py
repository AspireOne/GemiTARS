"""
Entry point for running the pi client as a module.

Usage: python -m pi_software
"""

import sys
import asyncio
from pathlib import Path

from .src.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Pi client stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)