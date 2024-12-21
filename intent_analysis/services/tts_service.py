import requests
import pydub
from pydub.playback import play
from core.logger import info, warning, error

def text_to_speech(text: str, tts_config: dict, output_file: str = "speech.mp3"):
    """
    Simple text-to-speech service that calls an OpenAI-compatible endpoint.
    """
    payload = {
        "model": tts_config["default_model"],
        "input": text,
        "voice": tts_config["default_voice"],
        "response_format": tts_config["response_format"],
        "speed": tts_config["default_speed"],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tts_config['api_key']}",
    }

    try:
        response = requests.post(tts_config["api_url"], headers=headers, json=payload)
        response.raise_for_status()

        # Save audio content to file
        with open(output_file, "wb") as f:
            f.write(response.content)

        info(f"Audio saved to {output_file}")
        audio = pydub.AudioSegment.from_file(output_file, format=tts_config["response_format"])
        play(audio)

    except requests.exceptions.RequestException as e:
        error(f"TTS request error: {e}")
    except Exception as ex:
        error(f"Unexpected error in text_to_speech: {ex}")
