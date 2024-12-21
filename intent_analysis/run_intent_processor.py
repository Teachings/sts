# run_intent_processor.py

from core.config_loader import load_config
from processors.intent_processor import IntentProcessor
from core.logger import info, error

if __name__ == "__main__":
    try:
        config = load_config("config/config.yml")
        processor = IntentProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start IntentProcessor: {e}")
