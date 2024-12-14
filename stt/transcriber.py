from faster_whisper import WhisperModel
from scipy.io.wavfile import write
from helpers import log


def transcribe_audio_stream(audio_queue, sample_rate, model_name="base.en", device="cuda", compute_type="float16"):
    """Consumes audio chunks from the queue and transcribes them."""
    log("Loading Faster Whisper model...", level="INFO")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    transcription = []

    while True:
        audio_data = audio_queue.get()
        if audio_data is None:
            break

        temp_audio_path = "temp_audio.wav"
        write(temp_audio_path, sample_rate, audio_data)

        log("Transcribing audio...", level="INFO")
        segments, _ = model.transcribe(temp_audio_path)
        current_text = " ".join(segment.text for segment in segments)
        transcription.append(current_text)

        # Display current and full transcription
        log(f"Current Transcription: {current_text}", level="INFO", color="blue")
        log(f"Full Transcription: {' '.join(transcription)}", level="SUCCESS")
