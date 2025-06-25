import os
import queue
import threading
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

# --- Configuration ---
# It's recommended to set your API key as an environment variable
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# --- Audio Stream Configuration ---
# Define the audio format and properties. pcm_24000 is a good balance of quality and speed.
# Other options: pcm_16000, pcm_22050, pcm_44100
OUTPUT_FORMAT = "pcm_24000"
SAMPLE_RATE = 24000
DTYPE = "int16"  # PCM data from ElevenLabs is 16-bit signed integers

# --- Voice and Model Configuration ---
VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"  # Example voice, you can use any voice ID
MODEL_ID = "eleven_flash_v2_5" # A high-quality, versatile model


class AudioPlayer:
    """
    A class to handle streaming audio from an iterator and playing it in real-time.

    This class sets up a separate thread to fetch audio chunks from the generator
    and put them into a queue. The main thread then uses sounddevice to play
    audio from this queue, ensuring non-blocking, continuous playback.
    """
    def __init__(self, audio_generator, sample_rate, channels=1, dtype=DTYPE):
        self.audio_generator = audio_generator
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        
        self.queue = queue.Queue()
        self.stream_finished = threading.Event()
        self.playback_finished = threading.Event()
        
    def _fill_queue(self):
        """
        Target for the producer thread. Fetches audio chunks and puts them in the queue.
        """
        try:
            for chunk in self.audio_generator:
                if chunk:
                    self.queue.put(chunk)
        finally:
            # Signal that the generator has finished
            self.stream_finished.set()

    def _audio_callback(self, outdata, frames, time, status):
        """
        The callback function for the sounddevice stream.
        """
        if status:
            print(f"Audio callback status: {status}", flush=True)

        try:
            # Get all available data from the queue
            data = b''
            while not self.queue.empty():
                data += self.queue.get_nowait()
            
            # Convert bytes to a numpy array
            if data:
                audio_array = np.frombuffer(data, dtype=self.dtype)
                chunk_size = len(audio_array)
                
                if chunk_size >= frames:
                    outdata[:] = audio_array[:frames].reshape(-1, self.channels)
                    # Put the remaining audio back into the queue as bytes
                    remaining_bytes = audio_array[frames:].tobytes()
                    # This is a trick to put it at the front of the queue
                    q = list(self.queue.queue)
                    self.queue = queue.Queue()
                    self.queue.put(remaining_bytes)
                    for item in q:
                        self.queue.put(item)
                else:
                    # Pad with silence if not enough data
                    outdata[:chunk_size] = audio_array.reshape(-1, self.channels)
                    outdata[chunk_size:] = 0
            else:
                # If the queue is empty, check if the stream is finished
                if self.stream_finished.is_set():
                    # Stream is done and queue is empty, so we are done
                    outdata.fill(0)
                    raise sd.CallbackStop
                else:
                    # Stream is not finished, but queue is empty (network lag)
                    # Output silence and wait for more data
                    outdata.fill(0)
        except queue.Empty:
            # This case is similar to the one above
            if self.stream_finished.is_set():
                print("Stream finished and queue is empty.", flush=True)
                raise sd.CallbackStop
            outdata.fill(0)
        except Exception as e:
            print(f"Error in audio callback: {e}", flush=True)
            raise sd.CallbackStop

    def play(self):
        """
        Starts the audio playback.
        """
        # Start the producer thread to fill the queue
        producer_thread = threading.Thread(target=self._fill_queue)
        producer_thread.daemon = True
        producer_thread.start()

        print("Starting audio playback...", flush=True)
        try:
            # Start the sounddevice stream
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._audio_callback,
                finished_callback=self.playback_finished.set
            ):
                # Wait until playback is finished
                self.playback_finished.wait()

        except Exception as e:
            print(f"An error occurred during playback: {e}", flush=True)
        finally:
            # Ensure the producer thread has finished
            producer_thread.join(timeout=2)
            print("Audio playback completed.", flush=True)

def stream_and_play_text(text: str):
    """
    Main function to stream text from ElevenLabs and play it.
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set.")
    
    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    
    print(f"Requesting audio stream for: '{text[:50]}...'")
    
    # Generate the audio stream from ElevenLabs
    # We request PCM data directly to avoid decoding MP3s on our side.
    audio_stream = client.text_to_speech.stream(
        text=text,
        voice_id=VOICE_ID, 
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            speed=1.0,
        ),
    )
    
    # Create and start the audio player
    player = AudioPlayer(audio_stream, SAMPLE_RATE)
    player.play()

def main():
    """
    Main entry point for the script.
    """
    # Make sure you have the required packages:
    # pip install elevenlabs sounddevice numpy python-dotenv
    
    test_text = (
        "Hello from Brno! This is a real-time audio stream directly from the "
        "ElevenLabs API, played using raw PCM data. "
        "By avoiding MP3 decoding, we achieve lower latency and a simpler, more robust pipeline."
    )
    
    try:
        stream_and_play_text(test_text)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
