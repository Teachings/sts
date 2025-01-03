import time
import queue
from faster_whisper import WhisperModel
from lightning_whisper_mlx import LightningWhisperMLX
from models import TranscriptionData, TranscriptionSegment
from helpers import log, display_transcriptions, save_transcription_to_json, load_config
import warnings
from post_processing import invoke_after_transcription

# Initialize global state with Pydantic objects
transcription_data = TranscriptionData()
current_transcription: list[TranscriptionSegment] = []
config = load_config()


def select_device():
    """
    Selects the best available device in order of priority:
    MPS (Apple Silicon) → NVIDIA GPU (CUDA) → CPU.
    Returns the selected device type as a string.
    """
    if "mps" in config.get("available_devices", ["mps"]):  # Check for MPS
        log("MPS (Apple Silicon) detected. Prioritizing for transcription.", level="INFO")
        return "mps"
    elif "cuda" in config.get("available_devices", ["cuda"]):  # Check for NVIDIA GPU
        log("NVIDIA GPU detected. Using CUDA for transcription.", level="INFO")
        return "cuda"
    else:  # Default to CPU
        log("No GPU detected. Falling back to CPU.", level="WARNING")
        return "cpu"


def initialize_model(model_name, device):
    """
    Initializes the transcription model based on the selected device.
    """
    try:
        if device == "mps":
            log(f"Using Lightning Whisper MLX model {model_name} on MPS (Apple Silicon).", level="INFO")
            return LightningWhisperMLX(model=model_name, batch_size=config.get("batch_size", 12))
        elif device == "cuda":
            log(f"Using Faster Whisper model {model_name} on NVIDIA GPU (CUDA).", level="INFO")
            return WhisperModel(model_name, device=device, compute_type=config.get("compute_type", "float16"))
        elif device == "cpu":
            log(f"Using Faster Whisper model {model_name} on CPU.", level="INFO")
            return WhisperModel(model_name, device=device, compute_type="int8")  # Optimized for CPU
        else:
            raise RuntimeError("No compatible model or device found for transcription.")
    except Exception as e:
        log(f"Error loading model: {str(e)}", level="ERROR")
        return None


def transcribe_audio_stream(audio_queue, sample_rate, model_name, device, shutdown_event=None):
    """
    Consumes filenames from the queue, transcribes them, and displays aggregated output.
    Groups transcriptions if they're less than 10 seconds apart.
    - Maintains method signature and contract for compatibility.
    """
    global transcription_data, current_transcription

    # Suppress warnings about sampling rate
    warnings.filterwarnings("ignore", category=UserWarning, message="Sampling rate is a multiply of 16000, casting to 16000 manually!")

    # Determine the best device
    selected_device = select_device() if device is None else device
    model = initialize_model(model_name, selected_device)
    if not model:
        return

    log(f"All systems active! Waiting for speech ...", level="SUCCESS")
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

            if isinstance(model, LightningWhisperMLX):
                # Transcription using Lightning Whisper MLX
                result = model.transcribe(audio_path=temp_file)
                current_text = result['text']
            elif isinstance(model, WhisperModel):
                # Transcription using Faster Whisper
                segments, _ = model.transcribe(temp_file, multilingual=True)
                current_text = " ".join(segment.text for segment in segments)
            else:
                raise RuntimeError("Unsupported device or model.")

            # Group transcriptions by time gap
            if last_timestamp is None or end_time - last_timestamp > time_gap_threshold:
                # Add existing transcription group to transcription_data
                if current_transcription:
                    transcription_data.transcriptions.append(
                        TranscriptionSegment(
                            timestamp=current_transcription[0].timestamp,
                            text=" ".join(segment.text for segment in current_transcription),
                            user=config.get("user", "default")
                        )
                    )
                current_transcription = []  # Start a new group

            # Add the new segment to the current transcription group
            latest_segment = TranscriptionSegment(
                timestamp=formatted_time,
                text=current_text,
                user=config.get("user", "default")
            )
            current_transcription.append(latest_segment)

            # Send the latest transcription to Kafka
            invoke_after_transcription(latest_segment)

            last_timestamp = end_time

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
                text=" ".join(segment.text for segment in current_transcription),
                user=config.get("user", "default")
            )
        )
    save_transcription_to_json(transcription_data)