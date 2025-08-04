"""
Button Manager: Handles physical button input using gpiod library.
"""

import asyncio
import time
from typing import Callable, Optional

from ..config.settings import Config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

ButtonPressedCallback = Callable[[], None]

class ButtonManager:
    """
    Manages physical button input with debouncing and asynchronous operation.
    """

    def __init__(self):
        self.enabled = Config.BUTTON_ENABLED
        self.gpio_pin = Config.BUTTON_GPIO_PIN
        self.debounce_delay = Config.BUTTON_DEBOUNCE_DELAY
        self.polling_interval = Config.BUTTON_POLLING_INTERVAL
        
        self.callback: Optional[ButtonPressedCallback] = None
        self.last_press_time = 0.0
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # GPIO components - will be initialized when starting
        self.chip = None
        self.line = None
        
        # Track button state for edge detection
        self.last_button_state = 1  # Assume button starts unpressed (pull-up)

    def set_callback(self, callback: ButtonPressedCallback):
        """Sets the function to call when button is pressed."""
        self.callback = callback

    async def start(self) -> bool:
        """
        Start monitoring the button. Returns True if successful, False otherwise.
        """
        if not self.enabled:
            logger.info("Button functionality is disabled in configuration")
            return True
            
        if Config.ENVIRONMENT != 'pi':
            logger.info("Button manager skipped - not running on Pi environment")
            return True
            
        try:
            # Import gpiod here to avoid import errors on non-Pi systems
            import gpiod
            
            # Set up GPIO
            self.chip = gpiod.Chip('gpiochip0')
            self.line = self.chip.get_line(self.gpio_pin)
            self.line.request(
                consumer="button_manager", 
                type=gpiod.LINE_REQ_DIR_IN, 
                flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
            )
            
            # Get initial state
            self.last_button_state = self.line.get_value()
            
            # Start monitoring task
            self.running = True
            self.monitor_task = asyncio.create_task(self._monitor_button())
            
            logger.info(f"Button manager started - monitoring GPIO pin {self.gpio_pin}")
            return True
            
        except ImportError:
            logger.warning("gpiod library not available - button functionality disabled")
            return True  # Not an error, just unavailable
        except Exception as e:
            logger.error(f"Failed to initialize button manager: {e}")
            return False

    async def stop(self):
        """Stop monitoring the button and clean up resources."""
        if not self.running:
            return
            
        logger.info("Stopping button manager...")
        self.running = False
        
        # Cancel monitoring task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        # Clean up GPIO resources
        if self.line:
            self.line.release()
            self.line = None
        self.chip = None
        
        logger.info("Button manager stopped")

    async def _monitor_button(self):
        """
        Continuously monitor the button state for presses.
        """
        try:
            while self.running:
                if self.line is None:
                    break
                    
                current_state = self.line.get_value()
                
                # Detect falling edge (button press) - from HIGH to LOW
                if self.last_button_state == 1 and current_state == 0:
                    await self._handle_button_press()
                
                self.last_button_state = current_state
                
                # Sleep for polling interval
                await asyncio.sleep(self.polling_interval)
                
        except asyncio.CancelledError:
            logger.debug("Button monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in button monitoring loop: {e}")
            # Try to continue monitoring unless we're shutting down
            if self.running:
                logger.info("Restarting button monitoring after error...")
                await asyncio.sleep(1.0)  # Brief delay before restart
                if self.running:  # Check again after delay
                    self.monitor_task = asyncio.create_task(self._monitor_button())

    async def _handle_button_press(self):
        """
        Handle a detected button press with debouncing.
        """
        current_time = time.time()
        
        # Check debounce delay
        if current_time - self.last_press_time < self.debounce_delay:
            logger.debug("Button press ignored due to debounce")
            return
        
        self.last_press_time = current_time
        logger.info("Button pressed!")
        
        # Trigger callback if set
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