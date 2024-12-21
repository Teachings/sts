import signal
import sys
import json
from abc import ABC, abstractmethod
from kafka import KafkaConsumer, KafkaProducer
from core.logger import info, warning, error, debug

class BaseKafkaProcessor(ABC):
    """
    BaseKafkaProcessor is an abstract class that sets up Kafka consumer/producer and
    handles signals for graceful shutdown. Subclasses must implement process_records().
    """
    def __init__(self, config):
        self.config = config
        kafka_config = config["kafka"]

        self.broker = kafka_config["broker"]
        self.consumer_group_id = kafka_config["consumer"]["group_id"]
        self.auto_offset_reset = kafka_config["consumer"]["auto_offset_reset"]

        self.consumer = None
        self.producer = None
        self.running = True
        self.is_shutting_down = False

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def init_consumer(self, topic_name: str):
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=self.broker,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
            group_id=self.consumer_group_id,
            value_deserializer=lambda x: x.decode("utf-8"),
        )
        info(f"KafkaConsumer initialized for topic '{topic_name}'")

    def init_producer(self):
        self.producer = KafkaProducer(
            bootstrap_servers=self.broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        info("KafkaProducer initialized")

    def shutdown(self):
        if not self.is_shutting_down:
            self.is_shutting_down = True
            warning("Shutting down gracefully...")
            self.running = False
            if self.consumer:
                self.consumer.close()
                info("KafkaConsumer closed")
            if self.producer:
                self.producer.close()
                info("KafkaProducer closed")

    def handle_signal(self, signal_number, frame):
        error(f"Received signal {signal_number}. Exiting...")
        self.shutdown()
        sys.exit(0)

    @abstractmethod
    def process_records(self):
        """
        Subclasses must implement this method to define
        how records are processed from the Kafka consumer.
        """
        pass

    def run(self):
        """
        The main entry point for processing. Subclasses typically
        won't override, but they can if needed.
        """
        try:
            self.process_records()
        except Exception as e:
            error(f"Unexpected error: {e}")
            self.shutdown()
            sys.exit(1)
