from core.config_loader import load_config
from processors.transcription_processor import TranscriptionProcessor
from core.logger import info, error

if __name__ == "__main__":
    try:
        config = load_config("config/config.yml")
        processor = TranscriptionProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start TranscriptionProcessor: {e}")
