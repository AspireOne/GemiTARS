## Immediate TODO

### Flow

1. Listening for a

### Gemini Live API

- Implement audio to audio streaming (from microphone) and play the audio stream

# TODO:
    # - Listen for a hotword
    # - When hotword is detected, start listening using Gemini Live API
    # - Gemini Live API will stream back audio.
    # - Play the audio
    
# Example request (not live!!)
    # response = client.models.generate_content(
    # model="gemini-2.5-flash",
    # contents="Explain how AI works in a few words",
    # config=types.GenerateContentConfig(
    #     thinking_config=types.ThinkingConfig(thinking_budget=0) # Disables thinking
    # )),
    # print(response[0].text)