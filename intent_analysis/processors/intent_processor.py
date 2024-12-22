import json
from core.base_processor import BaseKafkaProcessor
from core.logger import info, warning, error, debug
from services.tts_service import text_to_speech

class IntentProcessor(BaseKafkaProcessor):
    """
    IntentProcessor listens on the output topic of the transcription processor.
    It extracts the 'reasoning' from the message and plays it via TTS.
    """
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        self.consumer_group_id = kafka_config["consumer_groups"]["intent"]

        self.input_topic = kafka_config["actions_topic"]
        self.tts_config = config["text_to_speech"]

        # Initialize Kafka (only consumer needed)
        self.init_consumer(self.input_topic)

    def process_records(self):
        info(f"Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            raw_value = message.value
            debug(f"Received message: {raw_value}")

            # Attempt to parse JSON
            try:
                data = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
            except json.JSONDecodeError:
                error(f"Invalid JSON: {raw_value}")
                continue

            reasoning = data.get("reasoning", "")
            if reasoning:
                info(f"Speaking reasoning: {reasoning}")
                text_to_speech(reasoning, self.tts_config)

        self.shutdown()
