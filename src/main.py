import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Use env variable GEMINI_API_KEY.
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please set it in your environment or in a .env file. "
        "If using a .env file, install python-dotenv."
    )
client = genai.Client(api_key=api_key)

def main() -> None:
    print("Hello, world! Making a request to gemini...")
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain how AI works in a few words",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
    )),
    print(response[0].text)

if __name__ == "__main__":
    main()