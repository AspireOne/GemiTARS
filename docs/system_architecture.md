# TARS System Architecture

This document outlines the complete (CURRENT!) architecture of the TARS system, including the server and the Raspberry Pi client. It details the communication protocol, state management, and the interaction between the two components.

This document might be outdated.

## 1. WebSocket Communication Protocol

The client and server communicate over a WebSocket connection. The protocol consists of JSON control messages and binary audio data.

### Message Flow

The following diagram illustrates the typical message flow during a conversation:

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Client->>Server: { "type": "hotword_detected" }
    Server-->>Client: (Starts Gemini Session)
    Client->>Server: Binary Audio Stream (User Speech)
    Server-->>Client: Binary Audio Stream (TTS Response)
    Server-->>Client: { "type": "tts_stream_end" }
    Client->>Server: { "type": "playback_complete" }
    Note over Client,Server: Conversation continues...
    Server-->>Client: { "type": "session_end" }
```

## 2. Server-Side State Management

The server uses a state machine to manage the conversation flow. The state is managed by the `ConversationManager` class.

### Server States

- **PASSIVE**: The server is idle and waiting for a `hotword_detected` message from the client.
- **ACTIVE**: The server has received a hotword notification and is actively listening for user speech to stream to the Gemini API.
- **PROCESSING**: The server has received user speech and is waiting for a response from the Gemini API.
- **SPEAKING**: The server is streaming Text-to-Speech (TTS) audio to the client for playback.

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> PASSIVE

    PASSIVE --> ACTIVE: Hotword Detected
    ACTIVE --> PROCESSING: User Starts Speaking
    PROCESSING --> SPEAKING: Gemini Responds
    SPEAKING --> ACTIVE: TTS Finished
    ACTIVE --> PASSIVE: Timeout / Disconnect
```

## 3. Pi Client-Side State Management

The Pi client also uses a state machine to manage its lifecycle, from listening for a hotword to participating in an active conversation.

### Client States

- **IDLE**: The initial state before the client starts.
- **LISTENING_FOR_HOTWORD**: The client is actively listening for the "Hey TARS" hotword.
- **HOTWORD_DETECTED**: The hotword has been detected, and the client is preparing to connect to the server.
- **CONNECTING_TO_SERVER**: The client is establishing a WebSocket connection with the server.
- **ACTIVE_SESSION**: The client is connected to the server and is in an active conversation session.

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> LISTENING_FOR_HOTWORD: Start Client

    LISTENING_FOR_HOTWORD --> HOTWORD_DETECTED: Hotword Detected
    HOTWORD_DETECTED --> CONNECTING_TO_SERVER: Initiate Connection
    CONNECTING_TO_SERVER --> ACTIVE_SESSION: Connection Successful
    CONNECTING_TO_SERVER --> LISTENING_FOR_HOTWORD: Connection Failed

    ACTIVE_SESSION --> LISTENING_FOR_HOTWORD: Session Ends / Disconnects
```

## 4. State Machine Interaction

The client and server state machines are loosely coupled and interact primarily through the WebSocket message protocol. The following diagram illustrates how a state change on one side can trigger a state change on the other.

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Note over Client: State: LISTENING_FOR_HOTWORD
    Note over Server: State: PASSIVE

    Client->>Server: { "type": "hotword_detected" }
    Note over Client: State -> HOTWORD_DETECTED -> CONNECTING_TO_SERVER -> ACTIVE_SESSION
    Note over Server: State -> ACTIVE

    Client->>Server: Binary Audio Stream (User Speech)
    Note over Server: State -> PROCESSING

    Server-->>Client: Binary Audio Stream (TTS Response)
    Note over Server: State -> SPEAKING

    Server-->>Client: { "type": "tts_stream_end" }
    Client->>Server: { "type": "playback_complete" }
    Note over Server: State -> ACTIVE

    Server-->>Client: { "type": "session_end" }
    Note over Client: State -> LISTENING_FOR_HOTWORD
    Note over Server: State -> PASSIVE
```

This concludes the initial draft of the TARS system architecture documentation. Please review it and let me know if you would like any changes or additions.
