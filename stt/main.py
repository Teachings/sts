import argparse
import threading
import queue
from audio_utils import list_audio_devices, get_device_sampling_rate
from vad import load_vad_model, record_audio_stream
from transcriber import transcribe_audio_stream
from helpers import log

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Real-time audio transcription with VAD.")
    parser.add_argument("--model", type=str, default="base.en", help="Whisper model name (default: base.en)")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use for inference (default: cuda)")
    parser.add_argument("--rate", type=int, help="Override sampling rate (optional)")
    args = parser.parse_args()

    # List available audio devices
    devices = list_audio_devices()
    if not devices:
        log("No relevant audio devices found. Exiting.", level="ERROR")
        return

    log("Available audio devices:", level="INFO")
    for idx, name in devices.items():
        log(f"{idx}: {name}", level="INFO")

    # User selects an audio device
    try:
        device_id = int(input("Enter the device ID to use for recording: "))
    except ValueError:
        log("Invalid input. Exiting.", level="ERROR")
        return

    if device_id not in devices:
        log("Selected device is not valid. Exiting.", level="ERROR")
        return

    # Get the sampling rate
    sample_rate = args.rate or get_device_sampling_rate(device_id)
    log(f"Using sample rate: {sample_rate} Hz", level="INFO")

    # Load the VAD model
    vad_model, vad_utils = load_vad_model()

    # Queue for audio chunks
    audio_queue = queue.Queue()

    # Start threads for recording and transcription
    producer_thread = threading.Thread(
        target=record_audio_stream, args=(device_id, sample_rate, vad_model, vad_utils, audio_queue)
    )
    consumer_thread = threading.Thread(
        target=transcribe_audio_stream, args=(audio_queue, sample_rate, args.model, args.device)
    )

    try:
        producer_thread.start()
        consumer_thread.start()
        producer_thread.join()
        consumer_thread.join()
    except KeyboardInterrupt:
        log("Gracefully shutting down. Please wait...", level="WARNING")
        audio_queue.put(None)  # Signal consumer to stop
        producer_thread.join()
        consumer_thread.join()

if __name__ == "__main__":
    main()
