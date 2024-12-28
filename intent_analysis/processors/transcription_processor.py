from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, warning, error, debug
from agents.decision_agent import DecisionAgent

class TranscriptionProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]

        # Consumer config
        self.input_topic = kafka_cfg["transcriptions_topic"]
        group_id = kafka_cfg["consumer_groups"]["transcription"]

        # Producer config
        self.output_topic = kafka_cfg["actions_topic"]

        # Initialize Avro consumer with transcription schema
        self.init_consumer(group_id=group_id, topics=[self.input_topic], offset_reset="latest")

        # Initialize Avro producer with Action schema
        self.init_producer(
            producer_name="action_producer",
            avro_schema_file="schemas/action_value.avsc"
        )

        # The DecisionAgent logic remains the same
        self.decision_agent = DecisionAgent(config)

    def process_records(self):
        info(f"TranscriptionProcessor: Listening on {self.input_topic} (Avro)...")
        while self.running:
            try:
                msg = self.consumer.poll(1.0)  # poll for 1 second
                if msg is None:
                    continue
                if msg.error():
                    warning(f"TranscriptionProcessor consumer error: {msg.error()}")
                    continue

                # Avro-deserialized dict
                payload = msg.value()
                if not payload:
                    continue

                transcription = payload.get("text", "")
                user_id = payload.get("user", "UnknownUser")
                timestamp = payload.get("timestamp", "")

                # Evaluate with DecisionAgent
                decision = self.decision_agent.evaluate_transcription(transcription)
                debug(f"Decision object: {decision.model_dump()}")

                if decision.action_required_decision:
                    action_msg = {
                        "original_text": transcription,
                        "reasoning": decision.reasoning,
                        "categorization": decision.categorization,
                        "refined_prompt": decision.refined_prompt,
                        "user_id": user_id,
                        "timestamp": timestamp
                    }
                    # Produce to actions_topic with Action schema
                    self.produce_message(
                        producer_name="action_producer",
                        topic_name=self.output_topic,
                        value_dict=action_msg
                    )
                    info(f"TranscriptionProcessor: Published action to '{self.output_topic}'")
            except Exception as e:
                error(f"Error in TranscriptionProcessor: {e}")

        self.shutdown()
