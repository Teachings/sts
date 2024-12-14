import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from faster_whisper import WhisperModel

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

def record_audio(device_id, duration, sample_rate):
    """Records audio from the specified device."""
    print(f"Recording audio from device ID {device_id} ({duration} seconds at {sample_rate} Hz)...")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16', device=device_id)
    sd.wait()  # Wait until recording is finished
    return audio

def transcribe_audio(audio_path, model_name="base.en", device="cuda", compute_type="float16"):
    """Transcribes audio using Faster Whisper."""
    print("Loading Faster Whisper model...")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    
    print("Transcribing audio...")
    segments, _ = model.transcribe(audio_path)
    
    transcription = []
    for segment in segments:
        transcription.append(segment.text)
    
    return " ".join(transcription)

def main():
    # List available devices
    devices = list_audio_devices()
    
    if not devices:
        print("No relevant audio devices found. Exiting.")
        return
    
    print("Available audio devices:")
    for idx, name in devices.items():
        print(f"{idx}: {name}")
    
    # Select a device
    try:
        device_id = int(input("Enter the device ID to use for recording: "))
    except ValueError:
        print("Invalid input. Exiting.")
        return
    
    if device_id not in devices:
        print("Selected device is not valid. Exiting.")
        return
    
    # Get the sampling rate
    sample_rate = get_device_sampling_rate(device_id)
    print(f"Using sample rate: {sample_rate} Hz")
    
    # Record audio
    duration = 5  # seconds
    audio_data = record_audio(device_id, duration, sample_rate)
    
    # Save audio to a temporary file
    audio_path = "temp_audio.wav"
    write(audio_path, sample_rate, audio_data)
    print(f"Audio recorded and saved to {audio_path}")
    
    # Perform transcription
    transcription = transcribe_audio(audio_path)
    print("Transcription result:")
    print(transcription)

if __name__ == "__main__":
    main()
