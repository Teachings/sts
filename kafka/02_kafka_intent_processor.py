import json
import requests
import pydub
from pydub.playback import play
from kafka import KafkaConsumer
from termcolor import colored
import signal
import sys

# Kafka configurations
BROKER = "localhost:9092"
INPUT_TOPIC = "transcriptions.agent.action"
GROUP_ID = "text_to_speech_group"

# OpenAI-compatible endpoint
API_URL = "http://localhost:8000/v1/audio/speech"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {'sk-111111111'}"  # Replace with your API key
}

def text_to_speech(input_text, model="tts-1", voice="alloy", response_format="mp3", speed=0.75):
    payload = {
        "model": model,
        "input": input_text,
        "voice": voice,
        "response_format": response_format,
        "speed": speed
    }

    try:
        # Send the request to the API
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()

        # Save the audio to a file
        output_file = "speech.mp3"
        with open(output_file, "wb") as f:
            f.write(response.content)

        print(colored(f"Audio saved to {output_file}", 'green'))

        # Play the audio
        audio = pydub.AudioSegment.from_file(output_file, format=response_format)
        play(audio)

    except requests.exceptions.RequestException as e:
        print(colored(f"An error occurred while making the request: {e}", 'red'))

class KafkaIntentProcessor:
    def __init__(self, broker, topic_name, group_id):
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=broker,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=group_id,
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )
        self.running = True
        self.is_stopped = False  # Flag to prevent duplicate stopping

    def stop(self):
        if not self.is_stopped:
            self.is_stopped = True
            print(colored("Shutting down gracefully...", "yellow"))
            self.consumer.close()

    def process_messages(self):
        print(colored(f"Listening to topic '{INPUT_TOPIC}'...", 'cyan'))
        try:
            for message in self.consumer:
                if not self.running:
                    break

                data = message.value
                reasoning = data.get("reasoning", "")
                if reasoning:
                    print(colored(f"Playing reasoning: {reasoning}", 'blue'))
                    text_to_speech(reasoning)
        except Exception as e:
            print(colored(f"An error occurred while processing messages: {e}", 'red'))
        finally:
            self.stop()

# Signal handler
def handle_signal(signal_number, frame):
    print(colored(f"Received signal {signal_number}. Exiting...", "red"))
    processor.stop()
    sys.exit(0)

if __name__ == "__main__":
    processor = KafkaIntentProcessor(
        broker=BROKER,
        topic_name=INPUT_TOPIC,
        group_id=GROUP_ID
    )

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        processor.process_messages()
    except Exception as e:
        print(colored(f"An unexpected error occurred: {e}", 'red'))
        processor.stop()
        sys.exit(1)
