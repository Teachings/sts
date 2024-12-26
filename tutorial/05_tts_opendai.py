import requests
import pydub
from pydub.playback import play

# OpenAI-compatible endpoint
API_URL = "http://localhost:8000/v1/audio/speech"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {'sk-111111111'}"  # fake API key for local
}

def text_to_speech(input_text):
    payload = {
        "model": "tts-1",
        "input": input_text,
        "voice": "alloy",
        "response_format": "mp3",
        "speed": 0.75
    }

    try:
        # Send the request to the API
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()

        # Save the audio to a file
        output_file = "speech.mp3"
        with open(output_file, "wb") as f:
            f.write(response.content)

        print(f"Audio saved to {output_file}")

        # Play the audio
        audio = pydub.AudioSegment.from_file(output_file, format="mp3")
        play(audio)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")

if __name__ == "__main__":
    # Get user input
    user_text = input("Enter the text you want to convert to speech: ")
    text_to_speech(user_text)
