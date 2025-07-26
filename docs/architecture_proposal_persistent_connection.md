# Architecture Proposal: Persistent WebSocket Connection

This document proposes a change to the TARS system architecture to utilize a persistent WebSocket connection between the Pi client and the server. This change addresses the latency issues inherent in the current on-demand connection model and improves the overall robustness and responsiveness of the system.

## 1. Proposed Changes

### Pi Client (`pi_software`)

1.  **`WebSocketClient` (`websocket_client.py`):**
    *   **Persistent Connection Loop:** The `connect()` method will be wrapped in a persistent loop that runs as a background task. This loop will attempt to connect on startup and will automatically try to reconnect with an exponential backoff strategy if the connection is lost.
    *   **Heartbeat:** A ping/pong heartbeat mechanism will be enabled to keep the connection alive and allow for early detection of a disconnected state.
    *   **Start/Stop Methods:** `start()` and `stop()` methods will be added to manage the lifecycle of the connection loop.

2.  **`SessionManager` (`session_manager.py`):**
    *   **Connection at Startup:** The `SessionManager` will start the `WebSocketClient`'s connection loop at application startup, not after a hotword is detected.
    *   **Simplified Session Handling:** The `handle_active_session()` method will be simplified. It will no longer be responsible for initiating the connection, only for sending the `hotword_detected` message.
    *   **Connection Lost Handling:** The `on_connection_lost()` callback will become more critical, triggering UI/state updates to reflect the disconnected status while the `WebSocketClient` handles reconnection in the background.

### Server (`server`)

1.  **`PiWebsocketService` (`pi_websocket_service.py`):**
    *   **Long-Lived Connections:** The `_connection_handler` will be updated to manage a long-lived connection. It will not tear down all resources on a disconnect but will instead wait for the client to reconnect.

2.  **`TARSAssistant` (`main.py`):**
    *   **Robust Disconnect Handling:** The `_on_client_disconnected` method will be updated to handle temporary disconnects gracefully. If a conversation is not active, it will simply log the event and wait for reconnection. If a session is active, it will end the session as it does now.

## 2. Pros and Cons

### Advantages

*   **Reduced Latency:** Eliminates connection setup time after a hotword, making the assistant feel significantly more responsive.
*   **Improved Reliability:** A persistent connection with a heartbeat provides real-time status awareness and enables robust reconnection logic.
*   **Enables Proactive Communication:** The server can push messages to the client at any time, enabling future features like notifications or alerts.

### Disadvantages

*   **Increased Complexity:** The client and server will require more complex logic to manage the connection lifecycle, including reconnection strategies and more robust error handling.

## 3. Conclusion

The move to a persistent WebSocket connection is a significant architectural improvement that will enhance the user experience and the overall robustness of the TARS system. The benefits of reduced latency and improved reliability far outweigh the modest increase in implementation complexity.