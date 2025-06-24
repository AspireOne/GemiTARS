- On this page

- [Session lifetime](https://ai.google.dev/gemini-api/docs/live-session#maximum-session-duration)
- [Context window compression](https://ai.google.dev/gemini-api/docs/live-session#context-window-compression)
- [Session resumption](https://ai.google.dev/gemini-api/docs/live-session#session-resumption)
- [Receiving a message before the session disconnects](https://ai.google.dev/gemini-api/docs/live-session#goaway-message)
- [Receiving a message when the generation is complete](https://ai.google.dev/gemini-api/docs/live-session#generation-complete-message)
- [What's next](https://ai.google.dev/gemini-api/docs/live-session#whats-next)

# Session management with Live API

- On this page
- [Session lifetime](https://ai.google.dev/gemini-api/docs/live-session#maximum-session-duration)
- [Context window compression](https://ai.google.dev/gemini-api/docs/live-session#context-window-compression)
- [Session resumption](https://ai.google.dev/gemini-api/docs/live-session#session-resumption)
- [Receiving a message before the session disconnects](https://ai.google.dev/gemini-api/docs/live-session#goaway-message)
- [Receiving a message when the generation is complete](https://ai.google.dev/gemini-api/docs/live-session#generation-complete-message)
- [What's next](https://ai.google.dev/gemini-api/docs/live-session#whats-next)

In the Live API, a session refers to a persistent
connection where input and output are streamed continuously over the same
connection (read more about [how it works](https://ai.google.dev/gemini-api/docs/live)).
This unique session design enables low latency and supports unique features, but
can also introduce challenges, like session time limits, and early termination.
This guide covers strategies for overcoming the session management challenges
that can arise when using the Live API.

## Session lifetime

Without compression, audio-only sessions are limited to 15 minutes,
and audio-video sessions are limited to 2 minutes. Exceeding these limits
will terminate the session (and therefore, the connection), but you can use
[context window compression](https://ai.google.dev/gemini-api/docs/live-session#context-window-compression) to extend sessions to
an unlimited amount of time.

The lifetime of a connection is limited as well, to around 10 minutes. When the
connection terminates, the session terminates as well. In this case, you can
configure a single session to stay active over multiple connections using
[session resumption](https://ai.google.dev/gemini-api/docs/live-session#session-resumption).
You'll also receive a [GoAway message](https://ai.google.dev/gemini-api/docs/live-session#goaway-message) before the
connection ends, allowing you to take further actions.

## Context window compression

To enable longer sessions, and avoid abrupt connection termination, you can
enable context window compression by setting the [contextWindowCompression](https://ai.google.dev/api/live#BidiGenerateContentSetup.FIELDS.ContextWindowCompressionConfig.BidiGenerateContentSetup.context_window_compression)
field as part of the session configuration.

In the [ContextWindowCompressionConfig](https://ai.google.dev/api/live#contextwindowcompressionconfig), you can configure a
[sliding-window mechanism](https://ai.google.dev/api/live#ContextWindowCompressionConfig.FIELDS.ContextWindowCompressionConfig.SlidingWindow.ContextWindowCompressionConfig.sliding_window)
and the [number of tokens](https://ai.google.dev/api/live#ContextWindowCompressionConfig.FIELDS.int64.ContextWindowCompressionConfig.trigger_tokens)
that triggers compression.

[Python](https://ai.google.dev/gemini-api/docs/live-session#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-session#javascript)More

```
from google.genai import types

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    context_window_compression=(
        # Configures compression with default parameters.
        types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        )
    ),
)

```

```
const config = {
  responseModalities: [Modality.AUDIO],
  contextWindowCompression: { slidingWindow: {} }
};

```

## Session resumption

To prevent session termination when the server periodically resets the WebSocket
connection, configure the [sessionResumption](https://ai.google.dev/api/live#BidiGenerateContentSetup.FIELDS.SessionResumptionConfig.BidiGenerateContentSetup.session_resumption)
field within the [setup configuration](https://ai.google.dev/api/live#BidiGenerateContentSetup).

Passing this configuration causes the
server to send [SessionResumptionUpdate](https://ai.google.dev/api/live#SessionResumptionUpdate)
messages, which can be used to resume the session by passing the last resumption
token as the [`SessionResumptionConfig.handle`](https://ai.google.dev/api/live#SessionResumptionConfig.FIELDS.string.SessionResumptionConfig.handle)
of the subsequent connection.

[Python](https://ai.google.dev/gemini-api/docs/live-session#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-session#javascript)More

```
import asyncio
from google import genai
from google.genai import types

client = genai.Client(api_key="GEMINI_API_KEY")
model = "gemini-live-2.5-flash-preview"

async def main():
    print(f"Connecting to the service with handle {previous_session_handle}...")
    async with client.aio.live.connect(
        model=model,
        config=types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            session_resumption=types.SessionResumptionConfig(
                # The handle of the session to resume is passed here,
                # or else None to start a new session.
                handle=previous_session_handle
            ),
        ),
    ) as session:
        while True:
            await session.send_client_content(
                turns=types.Content(
                    role="user", parts=[types.Part(text="Hello world!")]
                )
            )
            async for message in session.receive():
                # Periodically, the server will send update messages that may
                # contain a handle for the current state of the session.
                if message.session_resumption_update:
                    update = message.session_resumption_update
                    if update.resumable and update.new_handle:
                        # The handle should be retained and linked to the session.
                        return update.new_handle

                # For the purposes of this example, placeholder input is continually fed
                # to the model. In non-sample code, the model inputs would come from
                # the user.
                if message.server_content and message.server_content.turn_complete:
                    break

if __name__ == "__main__":
    asyncio.run(main())

```

```
import { GoogleGenAI, Modality } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: "GEMINI_API_KEY" });
const model = 'gemini-live-2.5-flash-preview';

async function live() {
  const responseQueue = [];

  async function waitMessage() {
    let done = false;
    let message = undefined;
    while (!done) {
      message = responseQueue.shift();
      if (message) {
        done = true;
      } else {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }
    return message;
  }

  async function handleTurn() {
    const turns = [];
    let done = false;
    while (!done) {
      const message = await waitMessage();
      turns.push(message);
      if (message.serverContent && message.serverContent.turnComplete) {
        done = true;
      }
    }
    return turns;
  }

console.debug('Connecting to the service with handle %s...', previousSessionHandle)
const session = await ai.live.connect({
  model: model,
  callbacks: {
    onopen: function () {
      console.debug('Opened');
    },
    onmessage: function (message) {
      responseQueue.push(message);
    },
    onerror: function (e) {
      console.debug('Error:', e.message);
    },
    onclose: function (e) {
      console.debug('Close:', e.reason);
    },
  },
  config: {
    responseModalities: [Modality.TEXT],
    sessionResumption: { handle: previousSessionHandle }
    // The handle of the session to resume is passed here, or else null to start a new session.
  }
});

const inputTurns = 'Hello how are you?';
session.sendClientContent({ turns: inputTurns });

const turns = await handleTurn();
for (const turn of turns) {
  if (turn.sessionResumptionUpdate) {
    if (turn.sessionResumptionUpdate.resumable && turn.sessionResumptionUpdate.newHandle) {
      let newHandle = turn.sessionResumptionUpdate.newHandle
      // ...Store newHandle and start new session with this handle here
    }
  }
}

  session.close();
}

async function main() {
  await live().catch((e) => console.error('got error', e));
}

main();

```

## Receiving a message before the session disconnects

The server sends a [GoAway](https://ai.google.dev/api/live#GoAway) message that signals that the current
connection will soon be terminated. This message includes the [timeLeft](https://ai.google.dev/api/live#GoAway.FIELDS.google.protobuf.Duration.GoAway.time_left),
indicating the remaining time and lets you take further action before the
connection will be terminated as ABORTED.

[Python](https://ai.google.dev/gemini-api/docs/live-session#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-session#javascript)More

```
async for response in session.receive():
    if response.go_away is not None:
        # The connection will soon be terminated
        print(response.go_away.time_left)

```

```
const turns = await handleTurn();

for (const turn of turns) {
  if (turn.goAway) {
    console.debug('Time left: %s\n', turn.goAway.timeLeft);
  }
}

```

## Receiving a message when the generation is complete

The server sends a [generationComplete](https://ai.google.dev/api/live#BidiGenerateContentServerContent.FIELDS.bool.BidiGenerateContentServerContent.generation_complete)
message that signals that the model finished generating the response.

[Python](https://ai.google.dev/gemini-api/docs/live-session#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-session#javascript)More

```
async for response in session.receive():
    if response.server_content.generation_complete is True:
        # The generation is complete

```

```
const turns = await handleTurn();

for (const turn of turns) {
  if (turn.serverContent && turn.serverContent.generationComplete) {
    // The generation is complete
  }
}

```

## What's next

Explore more ways to work with the Live API in the full
[Capabilities](https://ai.google.dev/gemini-api/docs/live) guide,
the [Tool use](https://ai.google.dev/gemini-api/docs/live-tools) page, or the
[Live API cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI.ipynb).
