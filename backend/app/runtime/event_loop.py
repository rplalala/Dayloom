"""Event-loop policy shared by local launchers and asynchronous resource probes."""

import asyncio
import sys


def create_api_loop() -> asyncio.AbstractEventLoop:
    """Use the selector required by async PostgreSQL on Windows."""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()
