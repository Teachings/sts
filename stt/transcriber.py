import os
import json
import time
import queue
from faster_whisper import WhisperModel
from helpers import log

# Global state for managing transcription context
transcription_data = {"transcriptions": []}
current_transcription = []

def transcribe_audio_stream(audio_queue, sample_rate, model_name="base.en", device="cuda", shutdown_event=None):
    """
    Consumes filenames from the queue, transcribes them, and displays aggregated output.
    Groups transcriptions if they're less than 10 seconds apart.
    """
    log("Loading Faster Whisper model...", level="INFO")
    try:
        model = WhisperModel(model_name, device=device, compute_type="float16")
    except Exception as e:
        log(f"Error loading Whisper model: {str(e)}", level="ERROR")
        return

    global transcription_data, current_transcription
    last_timestamp = None  # Track the last transcription's timestamp
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    time_gap_threshold = 10  # seconds

    while not shutdown_event.is_set():
        try:
            temp_file = audio_queue.get(timeout=1)  # Timeout to periodically check shutdown
            if temp_file is None:
                break

            # Timestamp when transcription is triggered
            end_time = time.time()
            formatted_time = time.strftime(timestamp_format, time.localtime(end_time))

            log(f"Transcribing audio from {temp_file}...", level="INFO")
            segments, _ = model.transcribe(temp_file)
            current_text = " ".join(segment.text for segment in segments)

            # Check time gap and group transcriptions accordingly
            if last_timestamp is None or end_time - last_timestamp > time_gap_threshold:
                # Add the current group to JSON if it exists
                if current_transcription:
                    transcription_data["transcriptions"].append({
                        "timestamp": current_transcription[0]["timestamp"],
                        "text": " ".join(item["text"] for item in current_transcription)
                    })

                # Start a new transcription group
                current_transcription = []

            # Add the current segment to the transcription group
            current_transcription.append({
                "timestamp": formatted_time,
                "text": current_text
            })

            # Update last timestamp
            last_timestamp = end_time

            # Generate the JSON structure
            json_output = generate_json(transcription_data, current_transcription)
            invoke_after_transcription(json_output)

            # Display aggregated transcriptions (only once per transcription)
            display_transcriptions(
                transcription_data["transcriptions"] + [{
                    "timestamp": current_transcription[0]["timestamp"],
                    "text": " ".join(item["text"] for item in current_transcription)
                }]
            )

        except queue.Empty:
            continue
        except Exception as e:
            log(f"Error during transcription: {str(e)}", level="ERROR")

    # Save any remaining transcriptions on shutdown
    if current_transcription:
        transcription_data["transcriptions"].append({
            "timestamp": current_transcription[0]["timestamp"],
            "text": " ".join(item["text"] for item in current_transcription)
        })
    save_transcription_to_json(transcription_data)


def clear_context():
    """
    Clears the current transcription context:
    - Saves the current transcription data to a JSON file.
    - Resets the transcription data and current transcription list.
    """
    global transcription_data, current_transcription

    if transcription_data["transcriptions"] or current_transcription:
        # Dump current transcriptions to disk
        save_transcription_to_json(transcription_data)

        # Clear in-memory data structures
        transcription_data = {"transcriptions": []}
        current_transcription = []

        log("Transcription context cleared. Starting fresh.", level="SUCCESS")
    else:
        log("No transcription data to clear. Context already empty.", level="INFO")


def display_transcriptions(transcriptions):
    """Displays aggregated transcriptions grouped by timestamps in green."""
    log("Aggregated Transcriptions:", level="SUCCESS")
    for entry in transcriptions:
        log(f"[{entry['timestamp']}] {entry['text']}", level="INFO", color="green")


def generate_json(transcription_data, current_transcription):
    """
    Generates the updated JSON structure after every transcription.
    This is where data is ready to be sent downstream or saved if required.
    """
    json_output = {
        "transcriptions": transcription_data["transcriptions"] + [
            {
                "timestamp": current_transcription[0]["timestamp"],
                "text": " ".join(item["text"] for item in current_transcription)
            }
        ]
    }
    return json_output


def invoke_after_transcription(json_output):
    """
    Placeholder method for external integrations after every transcription.
    Checks for specific phrases like 'clear context' and triggers actions.
    """
    # log(f"Generated JSON for downstream system: {json.dumps(json_output, indent=2)}", level="INFO")

    # Check if the last transcription contains the phrase "clear context"
    if json_output["transcriptions"]:
        last_transcription = json_output["transcriptions"][-1]  # Get the last transcription
        last_text = last_transcription["text"].lower()  # Make the text case-insensitive

        if "clear context" in last_text:
            log("Detected 'clear context' command. Clearing transcription context...", level="WARNING")
            clear_context()



def save_transcription_to_json(transcription_data):
    """Saves transcription data to a JSON file with a timestamped filename."""
    output_folder = os.getcwd()
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"transcriptions_{timestamp}.json"
    output_path = os.path.join(output_folder, filename)

    try:
        with open(output_path, "w") as json_file:
            json.dump(transcription_data, json_file, indent=4)
        log(f"Transcription saved to {output_path}", level="SUCCESS")
    except Exception as e:
        log(f"Error saving transcription to JSON: {str(e)}", level="ERROR")
