"""
Button Manager: Handles physical button input using gpiozero library.
"""

import asyncio
from typing import Callable, Optional

from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

ButtonPressedCallback = Callable[[], None]

class ButtonManager:
    """
    Manages a physical button using gpiozero's event-driven system.
    """

    def __init__(self):
        self.enabled = Config.BUTTON_ENABLED
        self.gpio_pin = Config.BUTTON_GPIO_PIN
        self.debounce_delay = Config.BUTTON_DEBOUNCE_DELAY
        
        self.callback: Optional[ButtonPressedCallback] = None
        self.button = None

    def set_callback(self, callback: ButtonPressedCallback):
        """Sets the function to call when the button is pressed."""
        self.callback = callback
        if self.button:
            self.button.when_pressed = self._handle_button_press

    async def start(self) -> bool:
        """
        Start monitoring the button. Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.info("Button functionality is disabled in configuration.")
            return True
            
        if Config.ENVIRONMENT != 'pi':
            logger.info("Button manager skipped - not running on a Pi environment.")
            return True
            
        try:
            # Import gpiozero here to avoid import errors on non-Pi systems
            from gpiozero import Button, Device
            from gpiozero.pins.pigpio import PiGPIOFactory
            
            # Use pigpio for better performance and stability
            Device.pin_factory = PiGPIOFactory()
            
            self.button = Button(
                self.gpio_pin,
                pull_up=True,
                bounce_time=self.debounce_delay
            )
            self.button.when_pressed = self._handle_button_press
            
            logger.info(f"Button manager started on GPIO pin {self.gpio_pin}")
            return True
            
        except ImportError:
            logger.warning("gpiozero or pigpio library not available - button functionality disabled.")
            return True  # Not an error, just unavailable
        except Exception as e:
            logger.error(f"Failed to initialize button manager: {e}")
            return False

    async def stop(self):
        """Stop monitoring the button and clean up resources."""
        if self.button:
            self.button.close()
            self.button = None
            logger.info("Button manager stopped and resources released.")

    def _handle_button_press(self):
        """
        Internal callback for when gpiozero detects a button press.
        """
        logger.info("Button pressed!")
        
        if self.callback:
            try:
                # Since this callback is executed in a different thread by gpiozero,
                # we need to safely call our asyncio-based callback on the main event loop.
                asyncio.run_coroutine_threadsafe(self._safe_callback(), asyncio.get_running_loop())
            except Exception as e:
                logger.error(f"Error scheduling button press callback: {e}")

    async def _safe_callback(self):
        """Safely execute the callback."""
        if self.callback:
            try:
                self.callback()
            except Exception as e:
                logger.error(f"Error in button press callback: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()