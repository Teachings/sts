import os
import time
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import torch
from helpers import log, load_config


def load_vad_model():
    """Load Silero VAD model."""
    log("Loading VAD model...", level="INFO")
    model, utils = torch.hub.load(repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=True)
    get_speech_timestamps, _, _, _, _ = utils
    log("VAD model loaded successfully!", level="SUCCESS")
    return model, get_speech_timestamps


def record_audio_stream(device_id, sample_rate, vad_model, vad_utils, audio_queue, shutdown_event):
    """Records audio in chunks using double-buffering and detects voice activity."""
    buffer_duration = 1  # seconds
    chunk_size = int(sample_rate * buffer_duration)
    end_speech_delay = load_config().get("end_speech_delay", 5)  # seconds to wait before concluding speech ended
    last_voice_time = None
    accumulated_audio = []

    temp_files = ["temp_audio_1.wav", "temp_audio_2.wav"]
    active_file_index = 0

    log("Recording and detecting voice activity. Press Ctrl+C to stop.", level="INFO")

    try:
        with sd.InputStream(device=device_id, channels=1, samplerate=sample_rate, dtype="int16") as stream:
            while not shutdown_event.is_set():
                # Read a chunk of audio
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
                    temp_file = temp_files[active_file_index]
                    log(f"End of speech detected. Saving to {temp_file}.", level="INFO")

                    write(temp_file, sample_rate, np.array(accumulated_audio, dtype=np.int16))
                    audio_queue.put(temp_file)

                    accumulated_audio.clear()
                    last_voice_time = None
                    active_file_index = 1 - active_file_index

    except Exception as e:
        log(f"Error during recording: {str(e)}", level="ERROR")
    finally:
        audio_queue.put(None)  # Signal transcription to stop
        log("Cleaning up temporary files...", level="INFO")
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
