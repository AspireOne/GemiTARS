"""
Simple test script for hotword detection functionality.

This script tests just the HotwordService independently to verify:
- OpenWakeWord model loading
- Audio capture and processing
- Detection callback execution

Usage: python src/test_hotword.py
"""

import os
import asyncio
import signal
import sys
from typing import Optional

import sounddevice as sd
import numpy as np

from services.hotword_service import HotwordService
from config import Config


class HotwordTester:
    """Simple tester for hotword detection functionality."""
    
    def __init__(self):
        self.hotword_service = HotwordService()
        self.audio_stream: Optional[sd.InputStream] = None
        self.detection_count = 0
        self.running = True
        
        # Setup detection callback
        self.hotword_service.set_activation_callback(self._on_detection)
        
    def _on_detection(self) -> None:
        """Callback when hotword is detected."""
        self.detection_count += 1
        print(f"\n🎉 Detection #{self.detection_count}! Hotword callback executed!")
        print("   (In real TARS, this would activate conversation mode)")
        
    async def run_test(self) -> None:
        """Run the hotword detection test."""
        print("🧪 TARS Hotword Detection Test")
        print("=" * 50)
        print(f"Model: {Config.HOTWORD_MODEL}")
        print(f"Threshold: {Config.HOTWORD_THRESHOLD}")
        print(f"Sample Rate: {Config.AUDIO_SAMPLE_RATE}Hz")
        print(f"Block Size: {Config.AUDIO_BLOCK_SIZE}")
        print("=" * 50)
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            # Start hotword detection
            self.hotword_service.start_detection()
            
            # Start audio capture
            await self._start_audio_capture()
            
            print(f"\n🎤 Listening for '{Config.HOTWORD_MODEL}'...")
            print("🔊 Speak clearly and wait for detection!")
            print("📊 Status will be shown every 10 seconds")
            print("⏹️  Press Ctrl+C to stop")
            print()
            
            # Run status monitoring
            await self._monitor_status()
            
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
        finally:
            await self._cleanup()
            
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n🛑 Received interrupt signal...")
        self.running = False
        
    async def _start_audio_capture(self) -> None:
        """Start audio capture for hotword detection."""
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"⚠️ Audio status: {status}")
                
            if self.running:
                try:
                    audio_bytes = indata.tobytes()
                    detected = self.hotword_service.process_audio_chunk(audio_bytes)
                    
                    # Optional: Show real-time detection attempts
                    # (Uncomment next line for verbose output)
                    # if detected: print("🔍 Processing audio chunk...")
                    
                except Exception as e:
                    print(f"❌ Error processing audio: {e}")
        
        # Create audio stream
        self.audio_stream = sd.InputStream(
            samplerate=Config.AUDIO_SAMPLE_RATE,
            blocksize=Config.AUDIO_BLOCK_SIZE,
            dtype=Config.AUDIO_DTYPE,
            channels=Config.AUDIO_CHANNELS,
            callback=audio_callback,
        )
        
        self.audio_stream.start()
        print("✅ Audio capture started")
        
    async def _monitor_status(self) -> None:
        """Monitor and display status periodically."""
        status_interval = 10  # seconds
        loop_count = 0
        
        while self.running:
            await asyncio.sleep(1)
            loop_count += 1
            
            # Show status every 10 seconds
            if loop_count % status_interval == 0:
                status = self.hotword_service.get_status()
                print(f"\n📊 Status Update (after {loop_count}s):")
                print(f"   Active: {status['is_active']}")
                print(f"   Buffer Size: {status['buffer_size']} samples")
                print(f"   Buffer Duration: {status['buffer_seconds']:.1f}s") 
                print(f"   Detections: {self.detection_count}")
                print(f"   Threshold: {status['threshold']}")
                print("   (Still listening...)\n")
                
    async def _cleanup(self) -> None:
        """Clean up resources."""
        print("\n🔄 Cleaning up...")
        
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
                print("✅ Audio stream closed")
            except Exception as e:
                print(f"⚠️ Error closing audio stream: {e}")
                
        self.hotword_service.stop_detection()
        print("✅ Hotword detection stopped")
        
        print(f"\n📈 Test Summary:")
        print(f"   Total Detections: {self.detection_count}")
        print(f"   Model Used: {Config.HOTWORD_MODEL}")
        print(f"   Threshold: {Config.HOTWORD_THRESHOLD}")
        print("✅ Test completed")


async def main():
    """Main test function."""
    print("🚀 Starting TARS Hotword Detection Test...\n")
    
    try:
        tester = HotwordTester()
        await tester.run_test()
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())