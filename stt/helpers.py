from termcolor import colored
from datetime import datetime
import json
import os
from models import TranscriptionData, TranscriptionSegment

def load_config():
    """Load configuration from config.json."""
    try:
        with open("config.json", "r") as config_file:
            return json.load(config_file)
    except Exception as e:
        log(f"Error loading config.json: {str(e)}", level="ERROR")
        return {
        "favorite_microphones": [],
        "broker": "",
        "topic": ""
        }


def log(message, level="INFO", color="cyan"):
    """Log messages with timestamp and optional color."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    levels = {"INFO": "cyan", "WARNING": "yellow", "ERROR": "red", "SUCCESS": "green"}
    level_color = levels.get(level.upper(), color)
    print(colored(f"[{timestamp}] [{level}] {message}", level_color))

def clear_context(transcription_data: TranscriptionData, current_transcription: list):
    """
    Clears the current transcription context:
    - Saves the current transcription data to a JSON file.
    - Resets the transcription data and current transcription list.
    """
    if transcription_data.transcriptions or current_transcription:
        # Dump current transcriptions to disk
        save_transcription_to_json(transcription_data)

        # Clear in-memory data structures
        transcription_data.transcriptions.clear()
        current_transcription.clear()

        log("Transcription context cleared. Starting fresh.", level="SUCCESS")
    else:
        log("No transcription data to clear. Context already empty.", level="INFO")

def save_transcription_to_json(transcription_data: TranscriptionData):
    """Saves transcription data to a JSON file with a timestamped filename."""
    output_folder = os.getcwd()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"transcriptions_{timestamp}.json"
    output_path = os.path.join(output_folder, filename)

    try:
        with open(output_path, "w") as json_file:
            json.dump(transcription_data.dict(), json_file, indent=4)
        log(f"Transcription saved to {output_path}", level="SUCCESS")
    except Exception as e:
        log(f"Error saving transcription to JSON: {str(e)}", level="ERROR")

def display_transcriptions(transcriptions: list[TranscriptionSegment]):
    """Displays aggregated transcriptions grouped by timestamps in green."""
    log("Aggregated Transcriptions:", level="SUCCESS")
    for entry in transcriptions:
        log(f"[{entry.timestamp}] {entry.text}", level="INFO", color="green")

def generate_json(transcription_data: TranscriptionData, current_transcription: list[TranscriptionSegment]):
    """
    Generates the updated JSON structure after every transcription.
    This is where data is ready to be sent downstream or saved if required.
    """
    json_output = {
        "transcriptions": transcription_data.transcriptions + [
            {
                "timestamp": current_transcription[0].timestamp,
                "text": " ".join(item.text for item in current_transcription)
            }
        ]
    }
    return json_output