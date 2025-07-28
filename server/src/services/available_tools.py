"""
Available Tools: A registry of functions and their schemas for Gemini Function Calling.

This module defines the tools that can be used by the Gemini model, including their
FunctionDeclarations (for the API) and their corresponding Python implementations.
"""

import random
from google.genai import types

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

# --- Tool Registry ---
# A mapping of tool names to their actual Python function implementations.
# This allows the GeminiService to dynamically call the correct function.
available_tools = {
    "tell_a_joke": tell_a_joke,
}

# --- Tool Schemas ---
# A list of all function declarations to be sent to the Gemini API.
tool_schemas = [
    tell_a_joke_declaration,
]