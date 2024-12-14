import numpy as np
import sounddevice as sd
import torch
from helpers import log
import time


def load_vad_model():
    """Load Silero VAD model."""
    log("Loading VAD model...", level="INFO")
    model, utils = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=True)
    get_speech_timestamps, _, _, _, _ = utils
    log("VAD model loaded successfully!", level="SUCCESS")
    return model, get_speech_timestamps


def record_audio_stream(device_id, sample_rate, vad_model, vad_utils, audio_queue):
    """Records audio in chunks and detects voice activity with end-of-speech delay."""
    buffer_duration = 1  # seconds
    chunk_size = int(sample_rate * buffer_duration)
    end_speech_delay = 2  # seconds to wait before concluding speech ended
    last_voice_time = None
    accumulated_audio = []

    log("Recording and detecting voice activity. Press Ctrl+C to stop.", level="INFO")

    try:
        with sd.InputStream(device=device_id, channels=1, samplerate=sample_rate, dtype="int16") as stream:
            while True:
                audio_chunk, _ = stream.read(chunk_size)
                audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0

                # Voice activity detection
                timestamps = vad_utils(audio_float32, vad_model, sampling_rate=sample_rate)
                current_time = time.time()

                if timestamps:
                    log("Voice detected...", level="INFO")
                    accumulated_audio.extend(audio_int16)
                    last_voice_time = current_time
                elif last_voice_time and (current_time - last_voice_time) > end_speech_delay:
                    # Speech has ended after the delay
                    log("End of speech detected. Sending audio for transcription.", level="INFO")
                    audio_queue.put(np.array(accumulated_audio, dtype=np.int16))
                    accumulated_audio.clear()
                    last_voice_time = None  # Reset voice time
    except KeyboardInterrupt:
        log("Stopping audio recording.", level="WARNING")
        audio_queue.put(None)  # Signal transcription to stop
    except Exception as e:
        log(f"Error during recording: {str(e)}", level="ERROR")
