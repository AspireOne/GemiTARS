"""
Main entry point for GemiTARS Pi Client
"""

import asyncio
from .core.state_machine import StateMachine
from .audio.pc_audio_manager import PcAudioManager
from .core.hotword_detector import HotwordDetector
from .services.websocket_client import PersistentWebSocketClient
from .services.session_manager import SessionManager
from .utils.logger import setup_logger

logger = setup_logger(__name__)

async def main():
    """Main application entry point."""
    logger.info("Starting GemiTARS Pi Client...")
    
    # Initialize components
    state_machine = StateMachine()
    audio_manager = PcAudioManager()
    hotword_detector = HotwordDetector()
    websocket_client = PersistentWebSocketClient()
    
    # Get event loop
    loop = asyncio.get_running_loop()
    
    # Create session manager
    session_manager = SessionManager(
        state_machine=state_machine,
        audio_manager=audio_manager,
        hotword_detector=hotword_detector,
        websocket_client=websocket_client,
        loop=loop
    )
    
    try:
        # Start the session manager (establishes persistent connection)
        await session_manager.start()
        
        logger.info("GemiTARS Pi Client ready. Say 'Hey TARS' to activate.")
        
        # Keep running until interrupted
        await asyncio.Event().wait()
        
    except asyncio.CancelledError:
        logger.info("Application cancelled")
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        await session_manager.shutdown()
        logger.info("GemiTARS Pi Client shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")