"""
Simple conversation state management for VAD integration.
"""
import os
from enum import Enum
from datetime import datetime, timedelta

from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(os.path.splitext(os.path.basename(__file__))[0])


class ConversationState(Enum):
    """Simple conversation states for VAD management."""
    PASSIVE = "passive"        # Waiting for hotword
    ACTIVE = "active"          # User can speak, listening
    PROCESSING = "processing"  # Gemini is generating response, mic is muted
    SPEAKING = "speaking"      # Assistant is playing TTS audio, mic is muted


class ConversationManager:
    """Simple state manager for conversation flow."""
    
    def __init__(self, conversation_timeout: int = Config.CONVERSATION_TIMEOUT_SECONDS):
        """
        Initialize conversation manager.
        
        Args:
            conversation_timeout: Seconds before returning to passive state
        """
        self.state = ConversationState.PASSIVE
        self.last_activity = datetime.now()
        self.conversation_timeout = conversation_timeout
        
    def transition_to(self, new_state: ConversationState) -> None:
        """Transition to a new conversation state."""
        old_state = self.state
        self.state = new_state
        self.last_activity = datetime.now()
        
        logger.info(f"State transition: {old_state.value} -> {new_state.value}")
        
    def is_conversation_timeout(self) -> bool:
        """Check if time since last activity exceeds the timeout."""
        time_since_activity = datetime.now() - self.last_activity
        return time_since_activity > timedelta(seconds=self.conversation_timeout)
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def should_listen_for_speech(self) -> bool:
        """Check if the assistant should be listening for speech."""
        return self.state == ConversationState.ACTIVE
        