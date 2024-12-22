from core.config_loader import load_config
from processors.persistence_processor import PersistenceProcessor
from core.logger import error

if __name__ == "__main__":
    try:
        config = load_config()
        processor = PersistenceProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start PersistenceProcessor: {e}")
