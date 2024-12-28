# File: core/base_avro_processor.py
import signal
import sys
from abc import ABC, abstractmethod
from confluent_kafka.avro import AvroConsumer, AvroProducer
from confluent_kafka.avro import load as avro_load

from core.logger import info, warning, error, debug

class BaseAvroProcessor(ABC):
    """
    A base class that provides an AvroConsumer and (optionally) an AvroProducer.
    Subclasses must implement process_records().
    """
    def __init__(self, config):
        self.config = config
        kafka_cfg = config["kafka"]
        self.broker = kafka_cfg["broker"]
        self.schema_registry_url = kafka_cfg["schema_registry_url"]

        self.running = True
        self.consumer = None
        self.producers = {}  # dictionary if we want multiple producers by topic or usage
        self.is_shutting_down = False

        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def init_consumer(self, group_id: str, topics: list[str], offset_reset="earliest"):
        """
        Create an AvroConsumer for the given topics.
        """
        consumer_conf = {
            "bootstrap.servers": self.broker,
            "group.id": group_id,
            "auto.offset.reset": offset_reset,
            "schema.registry.url": self.schema_registry_url
        }
        self.consumer = AvroConsumer(consumer_conf)
        self.consumer.subscribe(topics)
        info(f"AvroConsumer subscribed to topics: {topics}")

    def init_producer(self, producer_name: str, avro_schema_file: str):
        """
        Initialize an AvroProducer with a specified value schema.
        - You can call this multiple times if you produce different types of messages
        """
        value_schema = avro_load(avro_schema_file)
        producer_conf = {
            "bootstrap.servers": self.broker,
            "schema.registry.url": self.schema_registry_url
        }
        avro_producer = AvroProducer(
            producer_conf,
            default_value_schema=value_schema
        )
        self.producers[producer_name] = avro_producer
        info(f"AvroProducer '{producer_name}' initialized with schema {avro_schema_file}")

    def produce_message(self, producer_name: str, topic_name: str, value_dict: dict):
        """
        Send Avro-serialized message using a previously initialized producer.
        """
        if producer_name not in self.producers:
            error(f"Producer '{producer_name}' not found. Did you call init_producer()?")
            return

        try:
            self.producers[producer_name].produce(topic=topic_name, value=value_dict)
            self.producers[producer_name].flush()
            debug(f"Produced Avro message to '{topic_name}': {value_dict}")
        except Exception as e:
            error(f"Failed to produce Avro message to {topic_name}: {e}")

    def run(self):
        """
        The main loop for polling messages. Subclasses typically won't override.
        """
        try:
            self.process_records()
        except Exception as e:
            error(f"Unexpected error in AvroProcessor run(): {e}")
            self.shutdown()
            sys.exit(1)

    @abstractmethod
    def process_records(self):
        pass

    def shutdown(self):
        if not self.is_shutting_down:
            self.is_shutting_down = True
            warning("Shutting down gracefully...")
            self.running = False
            if self.consumer:
                self.consumer.close()
                info("AvroConsumer closed")
            for pname, prod in self.producers.items():
                # There's no explicit close() for AvroProducer, but flush if you want
                prod.flush()
                info(f"AvroProducer '{pname}' flushed")

    def handle_signal(self, signal_number, frame):
        error(f"Received signal {signal_number}. Exiting...")
        self.shutdown()
        sys.exit(0)
