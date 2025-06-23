import os
import asyncio

from dotenv import load_dotenv
import sounddevice as sd
import numpy as np

from services import GeminiService
from config import get_default_config

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please set it in your environment or in a .env file. "
        "If using a .env file, install python-dotenv."
    )

# Type assertion since we've checked api_key is not None
assert api_key is not None


async def receive_and_print_responses(gemini_service: GeminiService) -> None:
    """Receives and prints responses from the Gemini service."""
    print("Response receiver started.")
    full_gemini_response = ""
    
    async for response in gemini_service.receive_responses():
        # Handle Gemini's text output
        if response.text:
            print(response.text, end="", flush=True)
            full_gemini_response += response.text

        if response.is_turn_complete:
            if full_gemini_response.strip():
                print()  # Add a newline after a complete response from Gemini
            full_gemini_response = ""

        # Handle the transcription of the user's audio
        if response.transcription_text:
            if response.transcription_finished:
                print(f"\n> You said: {response.transcription_text}\n")
            else:
                print(f"> You said: {response.transcription_text}", end="\r")


async def main() -> None:
    print("Program started.")

    # Audio configuration - using centralized config for consistency
    # Note: You can also customize these via environment variables (e.g., TARS_AUDIO_SAMPLE_RATE=16000)
    config = get_default_config()
    samplerate = config.audio.sample_rate
    blocksize = config.audio.block_size
    dtype = config.audio.dtype
    channels = config.audio.channels

    # Initialize Gemini service with centralized configuration
    # Legacy API: gemini_service = GeminiService(api_key=str(api_key))  # Still works!
    gemini_service = GeminiService(api_key=str(api_key), config=config)

    def audio_callback(indata, frames, time, status):
        """This function is called by sounddevice for each audio chunk."""
        if status:
            print(status, flush=True)
        # Put the audio data into the Gemini service queue in a thread-safe way
        loop.call_soon_threadsafe(gemini_service.queue_audio, indata.tobytes())

    try:
        loop = asyncio.get_running_loop()

        async with gemini_service:
            print("Gemini session started.")

            # Start the concurrent tasks for sending audio and receiving responses
            sender_task = asyncio.create_task(gemini_service.start_audio_sender())
            receiver_task = asyncio.create_task(receive_and_print_responses(gemini_service))

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