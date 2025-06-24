- On this page

- [Overview of supported tools](https://ai.google.dev/gemini-api/docs/live-tools#tools-overview)
- [Function calling](https://ai.google.dev/gemini-api/docs/live-tools#function-calling)
- [Asynchronous function calling](https://ai.google.dev/gemini-api/docs/live-tools#async-function-calling)
- [Code execution](https://ai.google.dev/gemini-api/docs/live-tools#code-execution)
- [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/live-tools#google-search)
- [Combining multiple tools](https://ai.google.dev/gemini-api/docs/live-tools#combine-tools)
- [What's next](https://ai.google.dev/gemini-api/docs/live-tools#whats-next)

# Tool use with Live API

- On this page
- [Overview of supported tools](https://ai.google.dev/gemini-api/docs/live-tools#tools-overview)
- [Function calling](https://ai.google.dev/gemini-api/docs/live-tools#function-calling)
- [Asynchronous function calling](https://ai.google.dev/gemini-api/docs/live-tools#async-function-calling)
- [Code execution](https://ai.google.dev/gemini-api/docs/live-tools#code-execution)
- [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/live-tools#google-search)
- [Combining multiple tools](https://ai.google.dev/gemini-api/docs/live-tools#combine-tools)
- [What's next](https://ai.google.dev/gemini-api/docs/live-tools#whats-next)

Tool use allows Live API to go beyond just conversation by enabling it to
perform actions in the real-world and pull in external context while maintaining
a real time connection.
You can define tools such as [Function calling](https://ai.google.dev/gemini-api/docs/function-calling),
[Code execution](https://ai.google.dev/gemini-api/docs/code-execution), and [Google Search](https://ai.google.dev/gemini-api/docs/grounding) with the Live API.

## Overview of supported tools

Here's a brief overview of the available tools for each model:

| Tool                 | Cascaded models<br>`gemini-live-2.5-flash-preview`<br>`gemini-2.0-flash-live-001` | `gemini-2.5-flash-preview-native-audio-dialog` | `gemini-2.5-flash-exp-native-audio-thinking-dialog` |
| -------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------------- |
| **Search**           | Yes                                                                               | Yes                                            | Yes                                                 |
| **Function calling** | Yes                                                                               | Yes                                            | No                                                  |
| **Code execution**   | Yes                                                                               | No                                             | No                                                  |
| **Url context**      | Yes                                                                               | No                                             | No                                                  |

## Function calling

Live API supports function calling, just like regular content generation
requests. Function calling lets the Live API interact with external data and
programs, greatly increasing what your applications can accomplish.

You can define function declarations as part of the session configuration.
After receiving tool calls, the client should respond with a list of
`FunctionResponse` objects using the `session.send_tool_response` method.

See the [Function calling tutorial](https://ai.google.dev/gemini-api/docs/function-calling) to learn
more.

[Python](https://ai.google.dev/gemini-api/docs/live-tools#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-tools#javascript)More

```
import asyncio
from google import genai
from google.genai import types

client = genai.Client(api_key="GEMINI_API_KEY")
model = "gemini-live-2.5-flash-preview"

# Simple function definitions
turn_on_the_lights = {"name": "turn_on_the_lights"}
turn_off_the_lights = {"name": "turn_off_the_lights"}

tools = [{"function_declarations": [turn_on_the_lights, turn_off_the_lights]}]
config = {"response_modalities": ["TEXT"], "tools": tools}

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        prompt = "Turn on the lights please"
        await session.send_client_content(turns={"parts": [{"text": prompt}]})

        async for chunk in session.receive():
            if chunk.server_content:
                if chunk.text is not None:
                    print(chunk.text)
            elif chunk.tool_call:
                function_responses = []
                for fc in chunk.tool_call.function_calls:
                    function_response = types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response={ "result": "ok" } # simple, hard-coded function response
                    )
                    function_responses.append(function_response)

                await session.send_tool_response(function_responses=function_responses)

if __name__ == "__main__":
    asyncio.run(main())

```

```
import { GoogleGenAI, Modality } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
const model = 'gemini-live-2.5-flash-preview';

// Simple function definitions
const turn_on_the_lights = { name: "turn_on_the_lights" } // , description: '...', parameters: { ... }
const turn_off_the_lights = { name: "turn_off_the_lights" }

const tools = [{ functionDeclarations: [turn_on_the_lights, turn_off_the_lights] }]

const config = {
  responseModalities: [Modality.TEXT],
  tools: tools
}

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
      } else if (message.toolCall) {
        done = true;
      }
    }
    return turns;
  }

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
    config: config,
  });

  const inputTurns = 'Turn on the lights please';
  session.sendClientContent({ turns: inputTurns });

  let turns = await handleTurn();

  for (const turn of turns) {
    if (turn.serverContent && turn.serverContent.modelTurn && turn.serverContent.modelTurn.parts) {
      for (const part of turn.serverContent.modelTurn.parts) {
        if (part.text) {
          console.debug('Received text: %s\n', part.text);
        }
      }
    }
    else if (turn.toolCall) {
      const functionResponses = [];
      for (const fc of turn.toolCall.functionCalls) {
        functionResponses.push({
          id: fc.id,
          name: fc.name,
          response: { result: "ok" } // simple, hard-coded function response
        });
      }

      console.debug('Sending tool response...\n');
      session.sendToolResponse({ functionResponses: functionResponses });
    }
  }

  // Check again for new messages
  turns = await handleTurn();

  for (const turn of turns) {
    if (turn.serverContent && turn.serverContent.modelTurn && turn.serverContent.modelTurn.parts) {
      for (const part of turn.serverContent.modelTurn.parts) {
        if (part.text) {
          console.debug('Received text: %s\n', part.text);
        }
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

From a single prompt, the model can generate multiple function calls and the
code necessary to chain their outputs. This code executes in a sandbox
environment, generating subsequent [BidiGenerateContentToolCall](https://ai.google.dev/api/live#bidigeneratecontenttoolcall) messages.

## Asynchronous function calling

Function calling executes sequentially by default, meaning execution pauses
until the results of each function call are available. This ensures sequential
processing, which means you won't be able to continue interacting with the model
while the functions are being run.

If you don't want to block the conversation, you can tell the model to run the
functions asynchronously. To do so, you first need to add a `behavior` to the
function definitions:

[Python](https://ai.google.dev/gemini-api/docs/live-tools#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-tools#javascript)More

```
  # Non-blocking function definitions
  turn_on_the_lights = {"name": "turn_on_the_lights", "behavior": "NON_BLOCKING"} # turn_on_the_lights will run asynchronously
  turn_off_the_lights = {"name": "turn_off_the_lights"} # turn_off_the_lights will still pause all interactions with the model

```

```
import { GoogleGenAI, Modality, Behavior } from '@google/genai';

// Non-blocking function definitions
const turn_on_the_lights = {name: "turn_on_the_lights", behavior: Behavior.NON_BLOCKING}

// Blocking function definitions
const turn_off_the_lights = {name: "turn_off_the_lights"}

const tools = [{ functionDeclarations: [turn_on_the_lights, turn_off_the_lights] }]

```

`NON-BLOCKING` ensures the function runs asynchronously while you can
continue interacting with the model.

Then you need to tell the model how to behave when it receives the
`FunctionResponse` using the `scheduling` parameter. It can either:

- Interrupt what it's doing and tell you about the response it got right away
  ( `scheduling="INTERRUPT"`),
- Wait until it's finished with what it's currently doing
  ( `scheduling="WHEN_IDLE"`),
- Or do nothing and use that knowledge later on in the discussion
  ( `scheduling="SILENT"`)

[Python](https://ai.google.dev/gemini-api/docs/live-tools#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-tools#javascript)More

```
# for a non-blocking function definition, apply scheduling in the function response:
  function_response = types.FunctionResponse(
      id=fc.id,
      name=fc.name,
      response={
          "result": "ok",
          "scheduling": "INTERRUPT" # Can also be WHEN_IDLE or SILENT
      }
  )

```

```
import { GoogleGenAI, Modality, Behavior, FunctionResponseScheduling } from '@google/genai';

// for a non-blocking function definition, apply scheduling in the function response:
const functionResponse = {
  id: fc.id,
  name: fc.name,
  response: {
    result: "ok",
    scheduling: FunctionResponseScheduling.INTERRUPT  // Can also be WHEN_IDLE or SILENT
  }
}

```

## Code execution

You can define code execution as part of the session configuration.
This lets the Live API generate and execute Python code and dynamically
perform computations to benefit your results. See the [Code execution tutorial](https://ai.google.dev/gemini-api/docs/code-execution) to learn more.

[Python](https://ai.google.dev/gemini-api/docs/live-tools#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-tools#javascript)More

```
import asyncio
from google import genai
from google.genai import types

client = genai.Client(api_key="GEMINI_API_KEY")
model = "gemini-live-2.5-flash-preview"

tools = [{'code_execution': {}}]
config = {"response_modalities": ["TEXT"], "tools": tools}

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        prompt = "Compute the largest prime palindrome under 100000."
        await session.send_client_content(turns={"parts": [{"text": prompt}]})

        async for chunk in session.receive():
            if chunk.server_content:
                if chunk.text is not None:
                    print(chunk.text)

                model_turn = chunk.server_content.model_turn
                if model_turn:
                    for part in model_turn.parts:
                      if part.executable_code is not None:
                        print(part.executable_code.code)

                      if part.code_execution_result is not None:
                        print(part.code_execution_result.output)

if __name__ == "__main__":
    asyncio.run(main())

```

```
import { GoogleGenAI, Modality } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
const model = 'gemini-live-2.5-flash-preview';

const tools = [{codeExecution: {}}]
const config = {
  responseModalities: [Modality.TEXT],
  tools: tools
}

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
      } else if (message.toolCall) {
        done = true;
      }
    }
    return turns;
  }

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
    config: config,
  });

  const inputTurns = 'Compute the largest prime palindrome under 100000.';
  session.sendClientContent({ turns: inputTurns });

  const turns = await handleTurn();

  for (const turn of turns) {
    if (turn.serverContent && turn.serverContent.modelTurn && turn.serverContent.modelTurn.parts) {
      for (const part of turn.serverContent.modelTurn.parts) {
        if (part.text) {
          console.debug('Received text: %s\n', part.text);
        }
        else if (part.executableCode) {
          console.debug('executableCode: %s\n', part.executableCode.code);
        }
        else if (part.codeExecutionResult) {
          console.debug('codeExecutionResult: %s\n', part.codeExecutionResult.output);
        }
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

## Grounding with Google Search

You can enable Grounding with Google Search as part of the session
configuration. This increases the Live API's accuracy and prevents
hallucinations. See the [Grounding tutorial](https://ai.google.dev/gemini-api/docs/grounding) to
learn more.

[Python](https://ai.google.dev/gemini-api/docs/live-tools#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-tools#javascript)More

```
import asyncio
from google import genai
from google.genai import types

client = genai.Client(api_key="GEMINI_API_KEY")
model = "gemini-live-2.5-flash-preview"

tools = [{'google_search': {}}]
config = {"response_modalities": ["TEXT"], "tools": tools}

async def main():
    async with client.aio.live.connect(model=model, config=config) as session:
        prompt = "When did the last Brazil vs. Argentina soccer match happen?"
        await session.send_client_content(turns={"parts": [{"text": prompt}]})

        async for chunk in session.receive():
            if chunk.server_content:
                if chunk.text is not None:
                    print(chunk.text)

                # The model might generate and execute Python code to use Search
                model_turn = chunk.server_content.model_turn
                if model_turn:
                    for part in model_turn.parts:
                      if part.executable_code is not None:
                        print(part.executable_code.code)

                      if part.code_execution_result is not None:
                        print(part.code_execution_result.output)

if __name__ == "__main__":
    asyncio.run(main())

```

```
import { GoogleGenAI, Modality } from '@google/genai';

const ai = new GoogleGenAI({ apiKey: "GOOGLE_API_KEY" });
const model = 'gemini-live-2.5-flash-preview';

const tools = [{googleSearch: {}}]
const config = {
  responseModalities: [Modality.TEXT],
  tools: tools
}

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
      } else if (message.toolCall) {
        done = true;
      }
    }
    return turns;
  }

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
    config: config,
  });

  const inputTurns = 'When did the last Brazil vs. Argentina soccer match happen?';
  session.sendClientContent({ turns: inputTurns });

  const turns = await handleTurn();

  for (const turn of turns) {
    if (turn.serverContent && turn.serverContent.modelTurn && turn.serverContent.modelTurn.parts) {
      for (const part of turn.serverContent.modelTurn.parts) {
        if (part.text) {
          console.debug('Received text: %s\n', part.text);
        }
        else if (part.executableCode) {
          console.debug('executableCode: %s\n', part.executableCode.code);
        }
        else if (part.codeExecutionResult) {
          console.debug('codeExecutionResult: %s\n', part.codeExecutionResult.output);
        }
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

## Combining multiple tools

You can combine multiple tools within the Live API,
increasing your application's capabilities even more:

[Python](https://ai.google.dev/gemini-api/docs/live-tools#python)[JavaScript](https://ai.google.dev/gemini-api/docs/live-tools#javascript)More

```
prompt = """
Hey, I need you to do three things for me.

1. Compute the largest prime palindrome under 100000.
2. Then use Google Search to look up information about the largest earthquake in California the week of Dec 5 2024?
3. Turn on the lights

Thanks!
"""

tools = [\
    {"google_search": {}},\
    {"code_execution": {}},\
    {"function_declarations": [turn_on_the_lights, turn_off_the_lights]},\
]

config = {"response_modalities": ["TEXT"], "tools": tools}

# ... remaining model call

```

```
const prompt = `Hey, I need you to do three things for me.

1. Compute the largest prime palindrome under 100000.
2. Then use Google Search to look up information about the largest earthquake in California the week of Dec 5 2024?
3. Turn on the lights

Thanks!
`

const tools = [\
  { googleSearch: {} },\
  { codeExecution: {} },\
  { functionDeclarations: [turn_on_the_lights, turn_off_the_lights] }\
]

const config = {
  responseModalities: [Modality.TEXT],
  tools: tools
}

// ... remaining model call

```

## What's next

- Check out more examples of using tools with the Live API in the
  [Tool use cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LiveAPI_tools.ipynb).
- Get the full story on features and configurations from the
  [Live API Capabilities guide](https://ai.google.dev/gemini-api/docs/live-guide).
