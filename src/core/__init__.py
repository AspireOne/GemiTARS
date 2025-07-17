"""
Core package for GemiTARS conversation management.

This package contains core functionality for conversation state management
and VAD integration.
"""

from .conversation_state import ConversationManager, ConversationState

__all__ = ['ConversationManager', 'ConversationState']