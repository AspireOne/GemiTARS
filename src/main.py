import os
from typing import Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
import asyncio

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please set it in your environment or in a .env file. "
        "If using a .env file, install python-dotenv."
    )

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"
config: Any = {"response_modalities": ["TEXT"]}

async def main() -> None:
    print("Program started.")
    async with client.aio.live.connect(model=model, config=config) as session:
        print("Session started")
    # TODO:
    # - Listen for a hotword
    # - When hotword is detected, start listening using Gemini Live API
    # - Gemini Live API will stream back audio.
    # - Play the audio

if __name__ == "__main__":
    asyncio.run(main())
    
    
    

# Example request
    # response = client.models.generate_content(
    # model="gemini-2.5-flash",
    # contents="Explain how AI works in a few words",
    # config=types.GenerateContentConfig(
    #     thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
    # )),
    # print(response[0].text)