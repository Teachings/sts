from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, error
from services.tts_service import text_to_speech

class IntentProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]
        self.consumer_group_id = kafka_cfg["consumer_groups"]["intent"]
        self.input_topic = kafka_cfg["actions_topic"]
        self.tts_config = config["text_to_speech"]

        # Avro consumer for action messages
        self.init_consumer(
            group_id=self.consumer_group_id,
            topics=[self.input_topic],
            offset_reset="latest"
        )

    def process_records(self):
        info(f"IntentProcessor: Listening on topic '{self.input_topic}' (Avro)...")

        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    error(f"IntentProcessor consumer error: {msg.error()}")
                    continue

                data = msg.value()
                if not data:
                    continue

                reasoning = data.get("reasoning", "")
                if reasoning:
                    info(f"Speaking reasoning: {reasoning}")
                    text_to_speech(reasoning, self.tts_config)
            except Exception as e:
                error(f"IntentProcessor Error: {e}")

        self.shutdown()
