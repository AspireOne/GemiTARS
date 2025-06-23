import os
import asyncio
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
import sounddevice as sd
import numpy as np

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please set it in your environment or in a .env file. "
        "If using a .env file, install python-dotenv."
    )

client = genai.Client(api_key=api_key)
# Using the model from the documentation, which is more likely to work with the live API.
model = "gemini-live-2.5-flash-preview"
config: Any = {
    "response_modalities": ["TEXT"],
    # Adding input transcription to see what the model hears.
    "input_audio_transcription": {},
}

# The queue to hold audio chunks from the microphone
audio_queue = asyncio.Queue()

async def send_audio_from_queue(session: Any) -> None:
    """Takes audio chunks from a queue and sends them to the Gemini API."""
    print("Audio sender started.")
    while True:
        audio_chunk_bytes = await audio_queue.get()
        await session.send_realtime_input(
            audio=types.Blob(data=audio_chunk_bytes, mime_type="audio/pcm;rate=16000")
        )
        audio_queue.task_done()

async def receive_and_print_responses(session: Any) -> None:
    """Receives and prints responses from the Gemini API."""
    print("Response receiver started.")
    while True:
        full_gemini_response = ""
        async for response in session.receive():
            # Handle Gemini's text output
            if response.text:
                print(response.text, end="", flush=True)
                full_gemini_response += response.text

            if response.server_content and response.server_content.turn_complete:
                if full_gemini_response.strip():
                    print()  # Add a newline after a complete response from Gemini
                full_gemini_response = ""

            # Handle the transcription of the user's audio
            if (
                response.server_content
                and response.server_content.input_transcription
                and response.server_content.input_transcription.text
            ):
                transcript = response.server_content.input_transcription
                text = transcript.text.strip()
                if transcript.finished:
                    print(f"\n> You said: {text}\n")
                else:
                    print(f"> You said: {text}", end="\r")


async def main() -> None:
    print("Program started.")

    # Audio configuration
    samplerate = 16000  # 16kHz sample rate
    blocksize = 1600   # 100ms chunks
    dtype = 'int16'     # 16-bit PCM
    channels = 1       # Mono audio

    def audio_callback(indata, frames, time, status):
        """This function is called by sounddevice for each audio chunk."""
        if status:
            print(status, flush=True)
        # Put the audio data into the asyncio queue in a thread-safe way
        loop.call_soon_threadsafe(audio_queue.put_nowait, indata.tobytes())

    try:
        loop = asyncio.get_running_loop()

        async with client.aio.live.connect(model=model, config=config) as session:
            print("Gemini session started.")

            # Start the concurrent tasks for sending audio and receiving responses
            sender_task = asyncio.create_task(send_audio_from_queue(session))
            receiver_task = asyncio.create_task(receive_and_print_responses(session))

            # Start the microphone stream
            stream = sd.InputStream(
                samplerate=samplerate,
                blocksize=blocksize,
                dtype=dtype,
                channels=channels,
                callback=audio_callback,
            )
            with stream:
                print("\nMicrophone is open. Speak to start the conversation.")
                print("Press Ctrl+C to exit.")
                await asyncio.gather(sender_task, receiver_task)

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Shutting down.")