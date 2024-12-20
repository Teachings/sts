import time
import queue
from faster_whisper import WhisperModel
from models import TranscriptionData, TranscriptionSegment
from helpers import log, display_transcriptions, generate_json, save_transcription_to_json, load_config
from post_processing import invoke_after_transcription

# Initialize global state with Pydantic objects
transcription_data = TranscriptionData()
current_transcription: list[TranscriptionSegment] = []
config = load_config()

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
    last_timestamp = None
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    time_gap_threshold = config.get("time_gap_threshold", 60)

    while not shutdown_event.is_set():
        try:
            temp_file = audio_queue.get(timeout=1)  # Timeout to periodically check shutdown
            if temp_file is None:
                break

            end_time = time.time()
            formatted_time = time.strftime(timestamp_format, time.localtime(end_time))

            log(f"Transcribing audio from {temp_file}...", level="INFO")
            segments, _ = model.transcribe(temp_file)
            current_text = " ".join(segment.text for segment in segments)

            # Group transcriptions by time gap
            if last_timestamp is None or end_time - last_timestamp > time_gap_threshold:
                # Add existing transcription group to transcription_data
                if current_transcription:
                    transcription_data.transcriptions.append(
                        TranscriptionSegment(
                            timestamp=current_transcription[0].timestamp,
                            text=" ".join(segment.text for segment in current_transcription)
                        )
                    )
                current_transcription = []  # Start a new group

            # Add the new segment to the current transcription group
            current_transcription.append(
                TranscriptionSegment(timestamp=formatted_time, text=current_text)
            )

            last_timestamp = end_time

            # Generate and process JSON output
            json_output = generate_json(transcription_data, current_transcription)
            invoke_after_transcription(json_output)

            # Display transcriptions
            display_transcriptions(transcription_data.transcriptions + current_transcription)

        except queue.Empty:
            continue
        except Exception as e:
            log(f"Error during transcription: {str(e)}", level="ERROR")

    # Finalize and save remaining transcriptions on shutdown
    if current_transcription:
        transcription_data.transcriptions.append(
            TranscriptionSegment(
                timestamp=current_transcription[0].timestamp,
                text=" ".join(segment.text for segment in current_transcription)
            )
        )
    save_transcription_to_json(transcription_data)