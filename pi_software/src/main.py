"""
GemiTARS Raspberry Pi Client
"""

import asyncio
import signal
import platform

from .config.settings import Config
from .utils.logger import setup_logger
from .audio.pc_audio_manager import PcAudioManager
# TODO: Add PiAudioManager and a factory to select based on config/hardware
from .core.hotword_detector import HotwordDetector
from .core.state_machine import StateMachine
from .services.websocket_client import WebSocketClient
from .services.session_manager import SessionManager
 
# Note: Do not forget "sudo apt-get install -y portaudio19-dev" on Linux

logger = setup_logger(__name__)

class TarsClient:
    """
    Main client application class.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        # For now, we hardcode the PC audio manager.
        # A factory function would be used here in the future.
        self.audio_manager = PcAudioManager()
        self.hotword_detector = HotwordDetector()
        self.state_machine = StateMachine()
        self.websocket_client = WebSocketClient()
        self.session_manager = SessionManager(
            state_machine=self.state_machine,
            audio_manager=self.audio_manager,
            hotword_detector=self.hotword_detector,
            websocket_client=self.websocket_client,
            loop=self.loop
        )
        self.shutdown_event = asyncio.Event()

    async def run(self):
        """Initializes components and starts the main loop."""
        logger.info("TARS Client starting...")
        
        if not await self.audio_manager.initialize():
            logger.critical("Failed to initialize audio manager. Exiting.")
            return

        await self.session_manager.start()
        
        logger.info("TARS Client is running. Press Ctrl+C to exit.")
        await self.shutdown_event.wait()

    async def cleanup(self):
        """Gracefully shuts down all components."""
        logger.info("Shutting down TARS Client...")
        await self.audio_manager.cleanup()
        await self.websocket_client.disconnect()
        logger.info("Shutdown complete.")


async def main():
    """Main entry point for the client application."""
    loop = asyncio.get_running_loop()
    client = TarsClient(loop=loop)

    # Signal handling for graceful shutdown
    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, client.shutdown_event.set)
    else:
        # On Windows, signal handlers are not supported in the same way.
        # The user can still use Ctrl+C, which will raise a KeyboardInterrupt.
        pass

    try:
        await client.run()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user.")