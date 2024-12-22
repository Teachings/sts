from core.config_loader import load_config
from processors.real_time_processor import RealTimeProcessor
from core.logger import error

if __name__ == "__main__":
    try:
        config = load_config()
        processor = RealTimeProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start RealTimeProcessor: {e}")
