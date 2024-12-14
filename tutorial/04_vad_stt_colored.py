import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import torch
import queue
import threading
from termcolor import colored
from datetime import datetime
import argparse
import sys

def log(message, level="INFO", color="cyan"):
    """Log messages with a timestamp and optional color."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    levels = {"INFO": "cyan", "WARNING": "yellow", "ERROR": "red", "SUCCESS": "green"}
    level_color = levels.get(level.upper(), color)
    print(colored(f"[{timestamp}] [{level}] {message}", level_color))

def load_vad_model():
    """Load the Silero VAD model."""
    log("Loading VAD model...", level="INFO", color="yellow")
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)
    get_speech_timestamps, _, _, _, _ = utils
    log("VAD model loaded successfully!", level="SUCCESS")
    return model, get_speech_timestamps

def list_audio_devices():
    """Lists all available audio devices and filters relevant devices."""
    devices = sd.query_devices()
    relevant_devices = {
        idx: dev['name']
        for idx, dev in enumerate(devices)
        if "Elgato Wave XLR" in dev['name'] or "Jabra SPEAK 410 USB" in dev['name']
    }
    return relevant_devices

def get_device_sampling_rate(device_id):
    """Fetch the default sampling rate for the selected device."""
    return int(sd.query_devices(device_id)['default_samplerate'])

def record_audio(device_id, sample_rate, vad_model, vad_utils, audio_queue):
    """Records audio in chunks and detects voice activity."""
    buffer_duration = 1  # seconds
    chunk_size = int(sample_rate * buffer_duration)
    accumulated_audio = []  # Accumulate chunks with voice activity
    log("Recording started. Press Ctrl+C to stop recording.", level="INFO", color="yellow")

    try:
        with sd.InputStream(device=device_id, channels=1, samplerate=sample_rate, dtype='int16') as stream:
            while True:
                audio_chunk, _ = stream.read(chunk_size)
                audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0

                # Voice activity detection
                timestamps = vad_utils(audio_float32, vad_model, sampling_rate=sample_rate)
                if timestamps:
                    log("Voice detected...", level="INFO", color="green")
                    accumulated_audio.extend(audio_int16)
                elif accumulated_audio:
                    log("End of speech detected. Sending audio for transcription.", level="INFO", color="yellow")
                    audio_data = np.array(accumulated_audio, dtype=np.int16)
                    audio_queue.put(audio_data)
                    accumulated_audio.clear()  # Reset accumulator
    except KeyboardInterrupt:
        log("Recording stopped by user.", level="WARNING")
        audio_queue.put(None)  # Signal consumer to stop

def transcribe_audio(audio_queue, sample_rate, model_name="base.en", device="cuda", compute_type="float16"):
    """Consumes audio chunks from the queue and transcribes them."""
    log("Loading Faster Whisper model...", level="INFO", color="yellow")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    transcription = []

    try:
        while True:
            audio_data = audio_queue.get()
            if audio_data is None:
                break  # End signal from producer

            # Save audio chunk to temporary file
            temp_audio_path = "temp_audio.wav"
            write(temp_audio_path, sample_rate, audio_data)

            # Transcribe audio
            log("Transcribing audio...", level="INFO", color="blue")
            segments, _ = model.transcribe(temp_audio_path)
            transcribed_text = " ".join([segment.text for segment in segments])
            transcription.append(transcribed_text)
            log(f"Current Transcription: {transcribed_text}", level="INFO", color="green")
    except KeyboardInterrupt:
        log("Transcription interrupted by user.", level="WARNING")
    finally:
        log(f"Final Transcription: {' '.join(transcription)}", level="SUCCESS")

def graceful_shutdown(threads):
    """Gracefully shuts down threads."""
    log("Shutting down gracefully. Please wait...", level="INFO", color="yellow")
    for thread in threads:
        thread.join()
    log("Application terminated.", level="SUCCESS")

def main():
    """Main function to orchestrate the application."""
    parser = argparse.ArgumentParser(description="Real-time audio transcription with VAD.")
    parser.add_argument("--model", type=str, default="base.en", help="Whisper model name (default: base.en)")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use for inference (default: cuda)")
    parser.add_argument("--rate", type=int, help="Override sampling rate (optional)")
    args = parser.parse_args()

    # List available devices
    devices = list_audio_devices()
    if not devices:
        log("No relevant audio devices found. Exiting.", level="ERROR")
        sys.exit(1)

    log("Available audio devices:", level="INFO")
    for idx, name in devices.items():
        log(f"{idx}: {name}", level="INFO", color="cyan")

    # Select a device
    try:
        device_id = int(input(colored("Enter the device ID to use for recording: ", "yellow")))
        if device_id not in devices:
            raise ValueError
    except (ValueError, KeyboardInterrupt):
        log("Invalid device ID or operation canceled by user. Exiting.", level="ERROR")
        sys.exit(1)

    # Get the sampling rate
    sample_rate = args.rate or get_device_sampling_rate(device_id)
    log(f"Using sample rate: {sample_rate} Hz", level="INFO")

    # Load VAD model
    vad_model, vad_utils = load_vad_model()

    # Queue for audio chunks
    audio_queue = queue.Queue()

    # Start producer and consumer threads
    producer_thread = threading.Thread(target=record_audio, args=(device_id, sample_rate, vad_model, vad_utils, audio_queue))
    consumer_thread = threading.Thread(target=transcribe_audio, args=(audio_queue, sample_rate, args.model, args.device))

    threads = [producer_thread, consumer_thread]

    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        graceful_shutdown(threads)

if __name__ == "__main__":
    main()
