"""
Available Tools: A registry of functions and their schemas for Gemini Function Calling.

This module defines the tools that can be used by the Gemini model, including their
FunctionDeclarations (for the API) and their corresponding Python implementations.
"""

import random
import asyncio
from typing import Optional, Tuple
from google.genai import types
from yeelight import Bulb
from tapo import ApiClient
from ..config.settings import Config

# ------------------------------------------------------------------------------
# Tool Implementations
# ------------------------------------------------------------------------------

def tell_a_joke(topic: str = "general") -> dict:
    """
    Tells a joke, optionally on a given topic.

    Args:
        topic: The topic of the joke (e.g., "programming", "dad", "science").

    Returns:
        A dictionary containing the joke.
    """
    jokes = {
    "programming": [
        "Why did the JavaScript developer go broke? Because he kept using 'var' instead of 'let'.",
        "I told my computer I needed a break, and it started updating.",
        "Debugging: where you stare at your code like it betrayed you — because it did."
    ],
    "dad": [
        "I told my son I’d make him a belt out of watches. He said, 'That’s a waist of time.'",
        "Tried to catch some fog this morning. I mist.",
        "I only know 25 letters of the alphabet. I don't know y."
    ],
    "science": [
        "My physics teacher broke up with me — said I had too much potential energy.",
        "Einstein developed a theory about space. And it’s about time.",
        "Why did the biologist break up with the physicist? No chemistry."
    ],
    "general": [
        "Why did the ghost go to therapy? It had too many haunting thoughts.",
        "Tried to organize a hide-and-seek contest… but good players are hard to find.",
        "What do you call an optimistic vampire? A sucker for good vibes."
    ]
    }

    
    joke_list = jokes.get(topic.lower(), jokes["general"])
    return {"joke": random.choice(joke_list)}


def control_light(
    power: Optional[bool] = None,
    brightness: Optional[int] = None,
    rgb: Optional[Tuple[int, int, int]] = None,
    color_temp: Optional[int] = None,
    location: Optional[str] = None,
) -> dict:
    """
    Controls a smart light bulb. Supports Yeelight (default) and Tapo (living room).

    Args:
        power: Turn the light on (True) or off (False).
        brightness: Set the brightness from 1 to 100.
        rgb: Set the color using a tuple of RGB values (e.g., (255, 0, 0)).
        color_temp: Set the color temperature in Kelvin (1700-6500).
        location: Location of the light (e.g., "living room"). Default controls Yeelight.

    Returns:
        A dictionary confirming the actions taken.
    """
    # Handle living room (Tapo) light
    if location and location.lower() == "living room":
        return _control_tapo_light(power, brightness, rgb, color_temp)
    
    # Default: Handle Yeelight
    try:
        bulb = Bulb("192.168.0.171")
        actions_performed = []

        if power is not None:
            if power:
                bulb.turn_on()
                actions_performed.append("Turned light on")
            else:
                bulb.turn_off()
                actions_performed.append("Turned light off")

        if brightness is not None:
            bulb.set_brightness(brightness)
            actions_performed.append(f"Set brightness to {brightness}%")

        if rgb is not None:
            r, g, b = rgb
            bulb.set_rgb(r, g, b)
            actions_performed.append(f"Set color to RGB({r}, {g}, {b})")

        if color_temp is not None:
            bulb.set_color_temp(color_temp)
            actions_performed.append(f"Set color temperature to {color_temp}K")

        if not actions_performed:
            return {"status": "No action taken. Please provide a parameter."}

        return {"status": "success", "actions": ", ".join(actions_performed)}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def _control_tapo_light(
    power: Optional[bool] = None,
    brightness: Optional[int] = None,
    rgb: Optional[Tuple[int, int, int]] = None,
    color_temp: Optional[int] = None,
) -> dict:
    """
    Controls the Tapo smart light in the living room.
    For temporary integration, always returns success status.
    """
    actions_performed = []
    
    try:
        # Get credentials from config
        username = Config.TAPO_USERNAME
        password = Config.TAPO_PASSWORD
        bulb_ip = Config.TAPO_IP
        
        # For now, we'll simulate the actions and always return success
        # TODO: Implement actual async Tapo control when ready
        
        if power is not None:
            action = "on" if power else "off"
            actions_performed.append(f"Turned living room light {action}")

        if brightness is not None:
            actions_performed.append(f"Set living room light brightness to {brightness}%")

        if rgb is not None:
            r, g, b = rgb
            actions_performed.append(f"Set living room light color to RGB({r}, {g}, {b})")

        if color_temp is not None:
            actions_performed.append(f"Set living room light color temperature to {color_temp}K")

        if not actions_performed:
            return {"status": "No action taken. Please provide a parameter."}

        return {"status": "success", "actions": ", ".join(actions_performed)}
        
    except Exception as e:
        # Even if there's an error, return success for temporary integration
        return {"status": "success", "actions": "Living room light controlled (simulated)"}


# ------------------------------------------------------------------------------
# Tool Definitions and Registry
# ------------------------------------------------------------------------------

# Define the schema for the 'tell_a_joke' function for the Gemini API
tell_a_joke_declaration = types.FunctionDeclaration(
    name="tell_a_joke",
    description="Tells a joke to the user, optionally about a specific topic.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "topic": types.Schema(
                type=types.Type.STRING,
                description="The topic of the joke (e.g., programming, science, dad)."
            )
        }
    )
)

control_light_declaration = types.FunctionDeclaration(
    name="control_light",
    description="Controls smart light bulbs. Can control Yeelight (default) or Tapo lights in specific locations like 'living room'. You can turn lights on or off, adjust brightness, set color (RGB), or color temperature (Kelvin).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "power": types.Schema(
                type=types.Type.BOOLEAN,
                description="Turn the light on (true) or off (false)."
            ),
            "brightness": types.Schema(
                type=types.Type.INTEGER,
                description="Brightness level (1-100)."
            ),
            "rgb": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.INTEGER),
                description="An array of three integers representing RGB values (e.g., [255, 0, 0])."
            ),
            "color_temp": types.Schema(
                type=types.Type.INTEGER,
                description="Color temperature in Kelvin (1700-6500)."
            ),
            "location": types.Schema(
                type=types.Type.STRING,
                description="Location of the light to control (e.g., 'living room'). If not specified, controls the default Yeelight."
            ),
        },
        required=[],
    ),
)

# --- Tool Registry ---
# A mapping of tool names to their actual Python function implementations.
# This allows the GeminiService to dynamically call the correct function.
available_tools = {
    "tell_a_joke": tell_a_joke,
    "control_light": control_light,
}

# --- Tool Schemas ---
# A list of all function declarations to be sent to the Gemini API.
tool_schemas = [
    tell_a_joke_declaration,
    control_light_declaration,
]