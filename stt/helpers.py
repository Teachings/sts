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


def log(message, level="INFO", color=None):
    """Log messages with timestamp and optional color."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    levels = {"INFO": "cyan", "WARNING": "yellow", "ERROR": "red", "SUCCESS": "green"}
    
    # Convert level to uppercase to ensure case-insensitivity
    level_upper = level.upper()
    
    # Determine the color to use: if a color is provided, use it; otherwise, use the default for the level
    if color:
        level_color = color
    else:
        level_color = levels.get(level_upper, "cyan")  # Default to cyan if level is unknown
    
    print(colored(f"[{timestamp}] [{level_upper}] {message}", level_color))

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
    """Saves transcription data to a JSON file with a timestamped filename in a 'transcription_history' folder one level up."""
    # Get the current working directory
    output_folder = os.path.join(os.getcwd(), '.')
    
    # Define the path for the transcription_history folder
    transcription_history_folder = os.path.join(output_folder, 'transcription_history')
    
    # Create the transcription_history folder if it doesn't exist
    os.makedirs(transcription_history_folder, exist_ok=True)
    
    # Generate a timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"transcriptions_{timestamp}.json"
    
    # Construct the full output path
    output_path = os.path.join(transcription_history_folder, filename)
    
    # Save the transcription data to the JSON file
    with open(output_path, 'w') as f:
        json.dump(transcription_data.model_dump(), f, indent=4)

    try:
        with open(output_path, "w") as json_file:
            json.dump(transcription_data.model_dump(), json_file, indent=4)
        log(f"Transcription saved to {output_path}", level="SUCCESS")
    except Exception as e:
        log(f"Error saving transcription to JSON: {str(e)}", level="ERROR")

def display_transcriptions(transcriptions: list[TranscriptionSegment]):
    """Displays aggregated transcriptions grouped by timestamps in green."""
    log("Aggregated Transcriptions:", level="INFO")
    for entry in transcriptions:
        # log(f"[{entry.timestamp}] {entry.text}", level="INFO", color="green")
        log(f"{entry.text}", level="INFO", color="green")


def generate_json(transcription_data: TranscriptionData, current_transcription: list[TranscriptionSegment]):
    """
    Generates the updated JSON structure after every transcription.
    This is where data is ready to be sent downstream or saved if required.
    """
    json_output = {
        "transcriptions": transcription_data.transcriptions + [
            {
                "timestamp": current_transcription[0].timestamp,
                "text": " ".join(item.text for item in current_transcription),
                "user": load_config().get("user")
            }
        ]
    }
    return json_output