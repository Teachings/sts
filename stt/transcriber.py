import os
import json
import time
import queue
from faster_whisper import WhisperModel
from helpers import log, clear_context, display_transcriptions, generate_json, save_transcription_to_json
from post_processing import invoke_after_transcription  # Import functions from helpers

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

            # Invoke post-processing function
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