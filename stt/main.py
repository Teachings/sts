import argparse
import threading
import queue
import signal
from audio_utils import list_audio_devices, get_device_sampling_rate
from vad import load_vad_model, record_audio_stream
from transcriber import transcribe_audio_stream
from helpers import log 

# Global flag to signal threads to stop
shutdown_event = threading.Event()


def signal_handler(signal_received, frame):
    """Handle Ctrl+C or termination signals."""
    if not shutdown_event.is_set():
        log("Gracefully shutting down. Please wait...", level="WARNING")
        shutdown_event.set()  # Signal all threads to stop


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Real-time audio transcription with VAD.")
    parser.add_argument("--model", type=str, default="base.en", help="Whisper model name (default: base.en)")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use for inference (default: cuda)")
    parser.add_argument("--rate", type=int, help="Override sampling rate (optional)")
    args = parser.parse_args()

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # List available devices
    devices = list_audio_devices()
    if not devices:
        log("No relevant audio devices found. Exiting.", level="ERROR")
        return

    if len(devices) == 1:
        # Automatically use the single favorite microphone
        device_id, device_name = list(devices.items())[0]
        log(f"Using single favorite device: {device_name}", level="INFO")
    else:
        log("Available audio devices:", level="INFO")
        for idx, name in devices.items():
            log(f"{idx}: {name}", level="INFO")
        try:
            device_id = int(input("Enter the device ID to use for recording: "))
            if device_id not in devices:
                raise ValueError("Invalid device ID.")
        except ValueError:
            log("Invalid input. Exiting.", level="ERROR")
            return

    # Get the sampling rate
    sample_rate = args.rate or get_device_sampling_rate(device_id)
    log(f"Using sample rate: {sample_rate} Hz", level="INFO")

    # Load the VAD model
    vad_model, vad_utils = load_vad_model()

    # Queue for audio chunks (file names in this case)
    audio_queue = queue.Queue()

    # Start threads for recording and transcription
    producer_thread = threading.Thread(
        target=record_audio_stream, args=(device_id, sample_rate, vad_model, vad_utils, audio_queue, shutdown_event)
    )
    consumer_thread = threading.Thread(
        target=transcribe_audio_stream, args=(audio_queue, sample_rate, args.model, args.device, shutdown_event)
    )

    try:
        producer_thread.start()
        consumer_thread.start()
        producer_thread.join()
        consumer_thread.join()
    except Exception as e:
        log(f"Error occurred: {str(e)}", level="ERROR")
    finally:
        if not shutdown_event.is_set():
            shutdown_event.set()
        producer_thread.join()
        consumer_thread.join()
        log("All threads stopped. Exiting.", level="SUCCESS")

if __name__ == "__main__":
    main()
