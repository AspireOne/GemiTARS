"""
Available Tools: A registry of functions and their schemas for Gemini Function Calling.

This module defines the tools that can be used by the Gemini model, including their
FunctionDeclarations (for the API) and their corresponding Python implementations.
"""

import random
import asyncio
import colorsys
import logging
import os
from typing import Optional, Tuple
from pathlib import Path
from google.genai import types
from google import genai
from yeelight import Bulb
from tapo import ApiClient
from ..config.settings import Config
from ..utils.logger import setup_logger
from pydantic import BaseModel

logger = setup_logger(__name__)

# ------------------------------------------------------------------------------
# Tool Implementations
# ------------------------------------------------------------------------------

class SystemPromptUpdate(BaseModel):
    updated_system_prompt: str
    friendly_description_of_changes_made: str

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


def update_system_prompt(update_request: str) -> dict:
    """
    Updates the current persona's system prompt based on a user's request.
    This tool will intelligently rewrite the existing prompt to incorporate the requested changes.

    Args:
        update_request: A string describing the desired change (e.g., "Make it more affectionate,"
                        "Add a rule to always use tools for light changes.").

    Returns:
        A dictionary confirming the action or reporting an error.
    """
    if not update_request:
        return {"status": "error", "message": "Update request cannot be empty."}

    try:
        # --- Part 2: LLM-based Prompt Rewriting ---
        
        # 1. Get the current system prompt
        current_prompt = Config.get('SYSTEM_PROMPT', '')
        
        # 2. Load the editor prompt template
        prompt_template_path = Path(__file__).parent / "prompt_to_edit_system_prompt.txt"
        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            editor_prompt_template = f.read()
            
        # 3. Populate the template
        final_prompt = editor_prompt_template.replace("{{adjustments}}", update_request)
        final_prompt = final_prompt.replace("{{original_prompt}}", current_prompt)
        
        # 4. Call the editing LLM
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment.")
            return {"status": "error", "message": "GEMINI_API_KEY not found in environment."}
        
        logger.debug(f"prompt: {final_prompt}")
            
        client = genai.Client(api_key=api_key)
        _response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_prompt,
            config=types.GenerateContentConfig(
                temperature=0.45,
                response_mime_type="application/json",
                response_schema=SystemPromptUpdate,
                response_modalities=[types.Modality.TEXT],
            ),
        )
        
        response: SystemPromptUpdate = _response.parsed
        updated_system_prompt = response.updated_system_prompt.strip().replace("```", "").replace('"""', "")
        changes_description = response.friendly_description_of_changes_made
        
        logger.info("--- System Prompt Update ---")
        logger.info(f"Changes: {changes_description}")
        logger.info(f"New Prompt: {updated_system_prompt}")
        logger.info("--------------------------")
        
        # 5. Save the new prompt
        success = Config.set('SYSTEM_PROMPT', updated_system_prompt)
        
        if success:
            return {
                "status": "success",
                "message": f"Changes made: {changes_description}",
            }
        else:
            return {"status": "error", "message": "Failed to save the updated system prompt."}
            
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred during prompt update: {str(e)}"}


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


update_system_prompt_declaration = types.FunctionDeclaration(
    name="update_system_prompt",
    description="Intelligently updates the system prompt of the current persona based on a high-level request. Use this to modify the persona's personality, rules, or instructions.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "update_request": types.Schema(
                type=types.Type.STRING,
                description="A description of the change to make to the system prompt (e.g., 'Make the persona a little more sarcastic' or 'Add a rule that it must always greet the user by name')."
            )
        },
        required=["update_request"],
    ),
)


tool_schemas = [
    control_light_declaration,
    change_persona_declaration,
    update_system_prompt_declaration,
]

# --- Tool Registry ---
# A mapping of tool names to their actual Python function implementations.
# This allows the GeminiService to dynamically call the correct function.
available_tools = {
    "control_light": control_light,
    "change_persona": change_persona,
    "update_system_prompt": update_system_prompt,
}
