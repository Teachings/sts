import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import torch
import torchaudio

# Silero VAD model setup
def load_vad_model():
    """Load Silero VAD model."""
    print("Loading VAD model...")
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=True)
    get_speech_timestamps, _, _, _, _ = utils
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

def record_audio_stream(device_id, sample_rate, vad_model, vad_utils):
    """Records audio in chunks and detects voice activity."""
    buffer_duration = 1  # seconds
    chunk_size = int(sample_rate * buffer_duration)
    print("Recording and detecting voice activity. Speak into the microphone.")

    accumulated_audio = []  # Accumulate chunks with voice activity
    transcription = []  # Accumulate transcribed text
    try:
        with sd.InputStream(device=device_id, channels=1, samplerate=sample_rate, dtype='int16') as stream:
            while True:
                audio_chunk, _ = stream.read(chunk_size)
                audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                
                # Voice activity detection
                timestamps = vad_utils(audio_float32, vad_model, sampling_rate=sample_rate)
                if timestamps:
                    print("Voice detected...")
                    accumulated_audio.extend(audio_int16)
                elif accumulated_audio:
                    # When silence is detected after speech, save and transcribe
                    print("End of speech detected. Transcribing...")
                    audio_data = np.array(accumulated_audio, dtype=np.int16)
                    temp_audio_path = "temp_audio.wav"
                    write(temp_audio_path, sample_rate, audio_data)
                    
                    # Transcribe accumulated audio
                    transcription.append(transcribe_audio(temp_audio_path))
                    print("Current Transcription:", " ".join(transcription))
                    
                    accumulated_audio.clear()  # Reset accumulator
                    
    except KeyboardInterrupt:
        print("Recording stopped.")
        print("Final Transcription:", " ".join(transcription))
        return transcription

def transcribe_audio(audio_path, model_name="base.en", device="cuda", compute_type="float16"):
    """Transcribes audio using Faster Whisper."""
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(audio_path)
    return " ".join([segment.text for segment in segments])

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
    
    # Load VAD model
    vad_model, vad_utils = load_vad_model()
    
    # Record and transcribe with VAD
    record_audio_stream(device_id, sample_rate, vad_model, vad_utils)

if __name__ == "__main__":
    main()
