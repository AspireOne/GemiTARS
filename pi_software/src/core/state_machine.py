"""
Client State Machine
"""

from enum import Enum, auto
from typing import Callable, Dict, Set, Any

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class ClientState(Enum):
    """Defines the possible states of the client."""
    IDLE = auto()
    LISTENING_FOR_HOTWORD = auto()
    HOTWORD_DETECTED = auto()
    CONNECTING_TO_SERVER = auto()
    ACTIVE_SESSION = auto()

class StateMachine:
    """
    Manages the client's state and ensures valid transitions.
    """

    def __init__(self, initial_state: ClientState = ClientState.IDLE):
        self._state = initial_state
        self._transitions: Dict[ClientState, Set[ClientState]] = {
            ClientState.IDLE: {ClientState.LISTENING_FOR_HOTWORD},
            ClientState.LISTENING_FOR_HOTWORD: {ClientState.HOTWORD_DETECTED, ClientState.IDLE},
            ClientState.HOTWORD_DETECTED: {ClientState.CONNECTING_TO_SERVER},
            ClientState.CONNECTING_TO_SERVER: {ClientState.ACTIVE_SESSION, ClientState.LISTENING_FOR_HOTWORD},
            ClientState.ACTIVE_SESSION: {ClientState.LISTENING_FOR_HOTWORD, ClientState.IDLE}
        }
        self.on_state_change: Dict[ClientState, Callable[..., Any]] = {}

    @property
    def state(self) -> ClientState:
        """Returns the current state."""
        return self._state

    def can_transition_to(self, new_state: ClientState) -> bool:
        """Checks if a transition to a new state is valid."""
        return new_state in self._transitions.get(self._state, set())

    def transition_to(self, new_state: ClientState):
        """
        Transitions the state machine to a new state if the transition is valid.
        
        Args:
            new_state: The state to transition to.
            
        Returns:
            True if the transition was successful, False otherwise.
        """
        if self.can_transition_to(new_state):
            logger.info(f"State transition: {self._state.name} -> {new_state.name}")
            self._state = new_state
            # Trigger callback if one is registered for the new state
            if new_state in self.on_state_change:
                self.on_state_change[new_state]()
            return True
        else:
            logger.warning(f"Invalid state transition attempted: {self._state.name} -> {new_state.name}")
            return False

    def on_enter(self, state: ClientState, callback: Callable[..., Any]):
        """Registers a callback function to be executed upon entering a state."""
        self.on_state_change[state] = callback
