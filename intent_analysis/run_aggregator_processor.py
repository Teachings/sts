from core.config_loader import load_config
from processors.aggregator_processor import AggregatorProcessor
from core.logger import error

if __name__ == "__main__":
    try:
        config = load_config()
        processor = AggregatorProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start AggregatorProcessor: {e}")
