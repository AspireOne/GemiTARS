# Architecture Proposal: State-Driven Logic

This document proposes a refactoring of the Pi Client's architecture to simplify its logic by making the `StateMachine` the central, active component responsible for orchestrating the application's behavior.

## 1. Current Architecture and Problem

In the current V2 architecture, the `SessionManager` holds the primary application logic. It listens for events (e.g., hotword detection, WebSocket messages) and then manually directs other components, including telling the `StateMachine` when to change state.

**Problem:** This creates a separation between the *state* and the *logic that should execute in that state*. To understand what happens when the client is `LISTENING_FOR_HOTWORD`, one must look inside the `SessionManager`'s `_start_hotword_listening` method, rather than the `StateMachine` itself. This adds a layer of indirection that can make the control flow harder to follow and maintain.

## 2. Proposed Solution: A State-Driven Approach

I propose to refactor the client to follow a more traditional, robust state machine pattern where the logic is intrinsically tied to the state itself.

**The core idea is to move the action-oriented logic from the `SessionManager` into the `StateMachine` as `on_enter` handlers for each state.**

### 2.1. How it Would Work

The `StateMachine` will be enhanced to execute an asynchronous action upon entering a new state.

-   **`on_enter(LISTENING_FOR_HOTWORD)`:** This action will be responsible for:
    1.  Stopping any previous audio stream.
    2.  Starting a new audio recording.
    3.  Directing the audio chunks to the `HotwordDetector`.

-   **`on_enter(ACTIVE_SESSION)`:** This action will be responsible for:
    1.  Stopping the hotword detection audio stream.
    2.  Sending the `hotword_detected` message to the server.
    3.  Starting a new audio recording.
    4.  Directing the audio chunks to the `PersistentWebSocketClient` for streaming to the server.

-   **`on_enter(IDLE)`:** This action will ensure all audio streams are stopped and the client is in a quiescent state.

### 2.2. The Fate of `SessionManager`

With this change, the `SessionManager`'s role is drastically reduced. It no longer orchestrates the application's flow. Instead, it becomes a simple "event translator."

**Can it be eliminated entirely?**

Yes. The remaining responsibilities of the `SessionManager` can be absorbed by other components:

1.  **WebSocket Event Handling:** The callbacks for WebSocket events (`on_connected`, `on_disconnected`, `on_audio_received`, `on_control_message`) can be moved directly into the `main.py` application setup.
2.  **Hotword Callback:** The `on_hotword_detected` callback can also be handled in `main.py`.

The `main.py` file would then be responsible for initializing all the components (Audio Manager, Hotword Detector, WebSocket Client, State Machine) and wiring them together. For example, the `on_hotword_detected` callback would simply call `state_machine.transition_to(ClientState.HOTWORD_DETECTED)`. The `on_control_message` handler would parse the message and trigger the appropriate state transition (e.g., `state_machine.transition_to(ClientState.LISTENING_FOR_HOTWORD)` on a `session_end` message).

By eliminating the `SessionManager`, we remove a layer of abstraction and create a clearer, more direct control flow.

## 3. Benefits of the Proposed Refactoring

-   **Improved Clarity & Single Source of Truth:** The `StateMachine` becomes the undeniable source of truth for the application's behavior. The logic for each state is co-located with the state definition, making the system significantly easier to reason about.
-   **Reduced Complexity:** We eliminate an entire class (`SessionManager`) and the associated indirection. The control flow becomes more direct: an event triggers a state transition, and the state transition executes the corresponding action.
-   **Enhanced Maintainability:** When a bug occurs or a feature needs to be added, developers will know to look directly at the `StateMachine` definition for the relevant state, streamlining the development process.
-   **Better Testability:** A state-driven `StateMachine` is easier to unit test. We can test each state's entry action in isolation.

## 4. Implementation Plan

1.  **Enhance `StateMachine`:** Modify the `StateMachine` to support asynchronous `on_enter` actions.
2.  **Relocate Logic:**
    -   Move the logic from `SessionManager._start_hotword_listening` to a new `StateMachine.on_enter_listening_for_hotword` method.
    -   Move the logic from `SessionManager.start_session` to a new `StateMachine.on_enter_active_session` method.
    -   Create an `on_enter_idle` method to handle cleanup.
3.  **Refactor `main.py`:**
    -   Remove the `SessionManager` instantiation.
    -   Instantiate all other components directly in `main`.
    -   Set up the WebSocket and hotword callbacks in `main` to trigger the appropriate state transitions.
4.  **Delete `SessionManager`:** Remove the `pi_software/src/services/session_manager.py` file.
5.  **Update Documentation:** Update `docs/system_architecture_v2.md` to reflect the new, streamlined architecture.

This refactoring represents a significant improvement in the client's internal architecture, leading to a more robust, maintainable, and less complex system without changing its external behavior.