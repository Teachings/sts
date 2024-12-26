import requests
import pydub
from pydub.playback import play
from kafka import KafkaConsumer
from pydantic import BaseModel, Field, ValidationError
import json

# Kafka configurations
TOPIC_NAME = "text_to_speech"
BROKER = "localhost:9092"

# OpenAI-compatible endpoint
API_URL = "http://localhost:8000/v1/audio/speech"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {'sk-111111111'}"  # Replace with your API key
}

# Pydantic model for deserializing messages
class TranscriptionSegment(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the transcription")
    text: str = Field(..., description="Text of the transcription")
    user: str = Field(..., description="User Id")

def text_to_speech(segment: TranscriptionSegment):
    payload = {
        "model": "tts-1",
        "input": segment.text,
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

def consume_messages():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="text_to_speech_group",
        value_deserializer=lambda x: x.decode("utf-8")
    )

    print(f"Listening to topic '{TOPIC_NAME}'...")
    for message in consumer:
        try:
            # Deserialize the message value (JSON string) into a Pydantic object
            segment = TranscriptionSegment(**json.loads(message.value))
            print(f"Received TranscriptionSegment: {segment}")
            text_to_speech(segment)
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")
        except ValidationError as e:
            print(f"Validation error: {e}")

if __name__ == "__main__":
    consume_messages()
