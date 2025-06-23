"""
Simple VAD integration example for GemiTARS.

This demonstrates Phase 1 VAD integration:
- Conversation state management
- Basic interruption handling
- Speech completion detection
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
import sounddevice as sd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.gemini_service import GeminiService
from core.conversation_state import ConversationState

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")


async def handle_responses_with_vad(gemini_service: GeminiService) -> None:
    """Handle responses with VAD-aware conversation management."""
    print("VAD Response handler started.")
    full_response = ""
    
    async for response in gemini_service.receive_responses():
        # Check for interruption first
        if gemini_service.handle_interruption(response):
            full_response = ""  # Clear any partial response
            continue
            
        # Handle Gemini's text output
        if response.text:
            print(response.text, end="", flush=True)
            full_response += response.text

        # Handle speech completion detection
        if gemini_service.is_speech_complete(response):
            print(f"\n> You said: {response.transcription_text}")
            gemini_service.conversation_manager.transition_to(ConversationState.PROCESSING)
            
        # Handle turn completion
        if response.is_turn_complete:
            if full_response.strip():
                print()  # Add newline after complete response
            full_response = ""
            gemini_service.conversation_manager.transition_to(ConversationState.ACTIVE)
            
        # Handle transcription display
        if response.transcription_text and not response.transcription_finished:
            print(f"> You said: {response.transcription_text}", end="\r")
            
        # Check for conversation timeout
        if gemini_service.check_conversation_timeout():
            break


async def simulate_hotword_detection(gemini_service: GeminiService) -> None:
    """Simulate hotword detection for testing."""
    print("\nPress 'h' + Enter to simulate 'Hey TARS' hotword detection")
    print("Press 'q' + Enter to quit")
    
    while True:
        try:
            # Simple input simulation (in real implementation, this would be your hotword detector)
            user_input = await asyncio.get_event_loop().run_in_executor(None, input)
            
            if user_input.lower() == 'h':
                if gemini_service.conversation_manager.state == ConversationState.PASSIVE:
                    gemini_service.activate_conversation()
                else:
                    print("TARS: Already listening...")
                    
            elif user_input.lower() == 'q':
                print("TARS: Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\nTARS: Goodbye!")
            break


async def main_vad_example() -> None:
    """Main VAD example demonstrating Phase 1 integration."""
    print("TARS VAD Example - Phase 1")
    print("=" * 40)
    
    # Audio configuration (same as your existing setup)
    samplerate = 16000
    blocksize = 1600
    dtype = 'int16'
    channels = 1

    # Initialize Gemini service with VAD support
    gemini_service = GeminiService(api_key=str(api_key), enable_conversation_management=True)
    
    def audio_callback(indata, frames, time, status):
        """Audio callback with conversation state awareness."""
        if status:
            print(f"Audio status: {status}", flush=True)
        
        # Only process audio when in appropriate conversation state
        if gemini_service.conversation_manager.should_listen_for_speech():
            loop.call_soon_threadsafe(gemini_service.queue_audio, indata.tobytes())

    try:
        loop = asyncio.get_running_loop()
        
        # Start Gemini session
        async with gemini_service:
            print("TARS: System initialized. Waiting for hotword...")
            
            # Start concurrent tasks
            response_task = asyncio.create_task(handle_responses_with_vad(gemini_service))
            hotword_task = asyncio.create_task(simulate_hotword_detection(gemini_service))
            
            # Setup audio streaming
            stream = sd.InputStream(
                samplerate=samplerate,
                blocksize=blocksize,
                dtype=dtype,
                channels=channels,
                callback=audio_callback,
            )
            
            with stream:
                audio_task = asyncio.create_task(gemini_service.start_audio_sender())
                
                # Wait for any task to complete
                done, pending = await asyncio.wait(
                    [response_task, hotword_task, audio_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()

    except Exception as e:
        print(f"\nTARS: Error occurred: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main_vad_example())
    except KeyboardInterrupt:
        print("\nTARS: System shutdown.")