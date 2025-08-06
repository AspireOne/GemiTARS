"""
Available Tools: A registry of functions and their schemas for Gemini Function Calling.

This module defines the tools that can be used by the Gemini model, including their
FunctionDeclarations (for the API) and their corresponding Python implementations.
"""

import random
import asyncio
import colorsys
from typing import Optional, Tuple
from google.genai import types
from yeelight import Bulb
from tapo import ApiClient
from ..config.settings import Config

# ------------------------------------------------------------------------------
# Tool Implementations
# ------------------------------------------------------------------------------

def change_persona(persona_name: str) -> dict:
    """
    Changes the active persona to the specified one.

    Args:
        persona_name: The name of the persona to switch to.

    Returns:
        A dictionary confirming the action or reporting an error.
    """
    if not persona_name:
        return {"status": "error", "message": "Persona name cannot be empty."}

    available_personas = Config.get('AVAILABLE_PERSONAS', [])
    if persona_name not in available_personas:
        return {
            "status": "error",
            "message": f"Persona '{persona_name}' not found. "
                       f"Available personas are: {', '.join(available_personas)}"
        }

    success = Config.set('ACTIVE_PERSONA', persona_name)
    if success:
        return {"status": "success", "message": f"Active persona changed to {persona_name}."}
    else:
        return {"status": "error", "message": "Failed to change persona due to an internal error."}

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


async def control_light(
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
        return await _control_tapo_light(power, brightness, rgb, color_temp)
    
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


def _rgb_to_hsv_for_tapo(r: int, g: int, b: int) -> Tuple[int, int, int]:
    """Converts RGB (0-255) to HSV for Tapo (Hue: 0-360, Sat: 0-100, Val: 0-100)."""
    # Normalize RGB values to 0-1
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    # Convert to HSV
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    # Scale to Tapo's expected ranges
    hue = int(h * 360)
    saturation = int(s * 100)
    value = int(v * 100)
    return hue, saturation, value


async def _control_tapo_light(
    power: Optional[bool] = None,
    brightness: Optional[int] = None,
    rgb: Optional[Tuple[int, int, int]] = None,
    color_temp: Optional[int] = None,
) -> dict:
    """
    Controls the Tapo smart light in the living room using async operations.
    """
    actions_performed = []
    try:
        client = ApiClient(Config.TAPO_USERNAME, Config.TAPO_PASSWORD)
        bulb = await client.l530(Config.TAPO_IP)

        # Ensure light is on for color/brightness changes, unless explicitly turning off
        if power is not True and (brightness is not None or rgb is not None or color_temp is not None):
            await bulb.on()

        if power is not None:
            if power:
                await bulb.on()
                actions_performed.append("Turned living room light on")
            else:
                await bulb.off()
                actions_performed.append("Turned living room light off")

        # Handle color (RGB) conversion to Hue/Saturation
        if rgb is not None:
            r, g, b = rgb
            hue, saturation, value = _rgb_to_hsv_for_tapo(r, g, b)
            await bulb.set_hue_saturation(hue, saturation)
            actions_performed.append(f"Set living room light color to RGB({r}, {g}, {b})")
            # If brightness is not explicitly set, use the value from the RGB color
            if brightness is None:
                await bulb.set_brightness(value)
                actions_performed.append(f"Set brightness to {value}% (from RGB color)")

        # Handle brightness (takes precedence over RGB's value if both are provided)
        if brightness is not None:
            await bulb.set_brightness(brightness)
            actions_performed.append(f"Set living room light brightness to {brightness}%")

        if color_temp is not None:
            await bulb.set_color_temperature(color_temp)
            actions_performed.append(f"Set living room light color temperature to {color_temp}K")

        if not actions_performed:
            return {"status": "No action taken. Please provide a parameter."}

        return {"status": "success", "actions": ", ".join(actions_performed)}

    except Exception as e:
        return {"status": "error", "message": f"Tapo light error: {str(e)}"}


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

# --- Tool Schemas ---
# A list of all function declarations to be sent to the Gemini API.

# Dynamically create the description for the persona name parameter
available_personas_list = Config.get('AVAILABLE_PERSONAS', [])
persona_name_description = (
    "The name of the persona to switch to. "
    f"Available options are: {', '.join(available_personas_list)}"
)

change_persona_declaration = types.FunctionDeclaration(
    name="change_persona",
    description="Changes the active persona to a different one. This will change the bot's voice, personality, and system prompt.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "persona_name": types.Schema(
                type=types.Type.STRING,
                description=persona_name_description,
                enum=available_personas_list
            )
        },
        required=["persona_name"],
    ),
)

tool_schemas = [
    tell_a_joke_declaration,
    control_light_declaration,
    change_persona_declaration,
]

# --- Tool Registry ---
# A mapping of tool names to their actual Python function implementations.
# This allows the GeminiService to dynamically call the correct function.
available_tools = {
    "tell_a_joke": tell_a_joke,
    "control_light": control_light,
    "change_persona": change_persona,
}
