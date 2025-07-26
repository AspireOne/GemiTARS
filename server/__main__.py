"""
Entry point for running the server as a module.

Usage: python -m server
"""

import sys
import asyncio
from pathlib import Path

from .src.main import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)