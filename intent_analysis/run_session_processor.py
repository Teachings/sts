from core.config_loader import load_config
from processors.session_processor import SessionProcessor
from core.logger import error

if __name__ == "__main__":
    try:
        config = load_config()
        processor = SessionProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start SessionProcessor: {e}")
