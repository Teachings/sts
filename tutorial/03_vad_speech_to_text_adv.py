import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from faster_whisper import WhisperModel
import torch
import queue
import threading

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

def record_audio_stream(device_id, sample_rate, vad_model, vad_utils, audio_queue):
    """Records audio in chunks and detects voice activity."""
    buffer_duration = 1  # seconds
    chunk_size = int(sample_rate * buffer_duration)
    print("Recording and detecting voice activity. Speak into the microphone.")
    
    accumulated_audio = []  # Accumulate chunks with voice activity
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
                    # When silence is detected after speech, send audio to queue
                    print("End of speech detected. Sending audio for transcription.")
                    audio_data = np.array(accumulated_audio, dtype=np.int16)
                    audio_queue.put(audio_data)
                    accumulated_audio.clear()  # Reset accumulator
    except KeyboardInterrupt:
        print("Recording stopped.")
        audio_queue.put(None)  # Signal consumer to stop

def transcribe_audio_stream(audio_queue, sample_rate, model_name="base.en", device="cuda", compute_type="float16"):
    """Consumes audio chunks from the queue and transcribes them."""
    print("Loading Faster Whisper model...")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    transcription = []
    
    while True:
        audio_data = audio_queue.get()
        if audio_data is None:
            # End signal from producer
            break
        
        # Save audio chunk to temporary file
        temp_audio_path = "temp_audio.wav"
        write(temp_audio_path, sample_rate, audio_data)
        
        # Transcribe audio
        print("Transcribing audio...")
        segments, _ = model.transcribe(temp_audio_path)
        transcribed_text = " ".join([segment.text for segment in segments])
        transcription.append(transcribed_text)
        print("Current Transcription:", " ".join(transcription))
    
    print("Final Transcription:", " ".join(transcription))

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
    
    # Queue for audio chunks
    audio_queue = queue.Queue()
    
    # Start producer and consumer threads
    producer_thread = threading.Thread(target=record_audio_stream, args=(device_id, sample_rate, vad_model, vad_utils, audio_queue))
    consumer_thread = threading.Thread(target=transcribe_audio_stream, args=(audio_queue, sample_rate))
    
    producer_thread.start()
    consumer_thread.start()
    
    producer_thread.join()
    consumer_thread.join()

if __name__ == "__main__":
    main()
