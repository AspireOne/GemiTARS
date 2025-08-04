"""
Main entry point for GemiTARS Pi Client
"""

import asyncio
from .core.state_machine import StateMachine
from .core.hotword_detector import HotwordDetector
from .hardware.button_manager import ButtonManager
from .services.websocket_client import PersistentWebSocketClient
from .services.session_manager import SessionManager
from .services.local_sound_manager import LocalSoundManager
from .utils.logger import setup_logger
from .config.settings import Config

logger = setup_logger(__name__)

def get_audio_manager():
    """Factory function to get the appropriate audio manager."""
    if Config.ENVIRONMENT == 'pi':
        from .audio.pi_audio_manager import PiAudioManager
        logger.info("Using Pi Audio Manager")
        return PiAudioManager()
    # Default to PC audio manager
    from .audio.pc_audio_manager import PcAudioManager
    logger.info("Using PC Audio Manager")
    return PcAudioManager()

async def main():
    """Main application entry point."""
    logger.info("Starting GemiTARS Pi Client...")
    
    # Initialize components
    state_machine = StateMachine()
    audio_manager = get_audio_manager()

    # Initialize audio manager
    if not await audio_manager.initialize():
        logger.error("Failed to initialize audio manager. Exiting.")
        return
        
    # Initialize local sound manager
    local_sound_manager = LocalSoundManager()
    if not await local_sound_manager.initialize():
        logger.error("Failed to initialize local sound manager. Exiting.")
        return
        
    hotword_detector = HotwordDetector()
    websocket_client = PersistentWebSocketClient()
    
    # Initialize button manager
    button_manager = ButtonManager()
    if not await button_manager.start():
        logger.error("Failed to initialize button manager. Exiting.")
        return
    
    # Get event loop
    loop = asyncio.get_running_loop()
    
    # Create session manager
    session_manager = SessionManager(
        state_machine=state_machine,
        audio_manager=audio_manager,
        hotword_detector=hotword_detector,
        websocket_client=websocket_client,
        local_sound_manager=local_sound_manager,
        button_manager=button_manager,
        loop=loop
    )
    
    try:
        # Start the session manager (establishes persistent connection)
        await session_manager.start()
        
        logger.info("GemiTARS Pi Client ready. Say 'Hey TARS' or press the button to activate.")
        
        # Keep running until interrupted
        await asyncio.Event().wait()
        
    except asyncio.CancelledError:
        logger.info("Application cancelled")
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        await session_manager.shutdown()
        await button_manager.stop()
        logger.info("GemiTARS Pi Client shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")