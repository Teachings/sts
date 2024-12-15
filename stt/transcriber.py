import queue
from faster_whisper import WhisperModel
from helpers import log
import time


def transcribe_audio_stream(audio_queue, sample_rate, model_name="base.en", device="cuda", shutdown_event=None):
    """Consumes filenames from the queue and transcribes them with timestamps."""
    log("Loading Faster Whisper model...", level="INFO")
    try:
        model = WhisperModel(model_name, device=device, compute_type="float16")
    except Exception as e:
        log(f"Error loading Whisper model: {str(e)}", level="ERROR")
        return

    transcription = []
    last_timestamp = None  # Track the last transcription's timestamp
    timestamp_format = "%Y-%m-%d %H:%M:%S"

    while not shutdown_event.is_set():
        try:
            temp_file = audio_queue.get(timeout=1)  # Timeout to periodically check shutdown
            if temp_file is None:
                break

            log(f"Transcribing audio from {temp_file}...", level="INFO")
            start_time = time.time()  # Timestamp for this transcription segment
            segments, _ = model.transcribe(temp_file)
            current_text = " ".join(segment.text for segment in segments)

            # Check time gap for adding a timestamp
            if last_timestamp is None or start_time - last_timestamp > 15:
                formatted_time = time.strftime(timestamp_format, time.localtime(start_time))
                transcription.append(f"[{formatted_time}]")  # Add a new timestamp
                log(f"Timestamp added: {formatted_time}", level="INFO")

            transcription.append(current_text)
            last_timestamp = start_time  # Update the last timestamp

            # Display current and full transcriptions
            log(f"Current Transcription: {current_text}", level="INFO", color="blue")
            log(f"Full Transcription: {' '.join(transcription)}", level="SUCCESS")
        except queue.Empty:
            continue
        except Exception as e:
            log(f"Error during transcription: {str(e)}", level="ERROR")
