import json
from core.base_processor import BaseKafkaProcessor
from core.logger import info, warning, error, debug
from agents.decision_agent import DecisionAgent, AgentDecision

class TranscriptionProcessor(BaseKafkaProcessor):
    """
    TranscriptionProcessor reads raw transcriptions from the configured topic,
    uses the DecisionAgent to determine if action is required, and publishes
    an action message if so.
    """
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        self.consumer_group_id = kafka_config["consumer_groups"]["transcription"]

        self.input_topic = kafka_config["transcriptions_topic"]
        self.output_topic = kafka_config["actions_topic"]

        # Initialize Kafka
        self.init_consumer(self.input_topic)
        self.init_producer()

        # Initialize the DecisionAgent
        self.decision_agent = DecisionAgent(config)

    def process_records(self):
        info(f"Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            raw_str = message.value
            payload = json.loads(raw_str)
            user_id = payload.get("user", "UnknownUser")
            transcription = payload.get("text", "")
            timestamp = payload.get("timestamp", "")
            
            debug(f"Received transcription: {transcription}")

            try:
                decision = self.decision_agent.evaluate_transcription(transcription)
                debug(f"Decision object: {decision.model_dump_json(indent=2)}")

                if decision.action_required_decision:
                    action_message = {
                        "original_transcription": transcription,
                        "refined_prompt": decision.refined_prompt,
                        "categorization": decision.categorization,
                        "reasoning": decision.reasoning,
                    }
                    self.producer.send(self.output_topic, action_message)
                    info(f"Published action to '{self.output_topic}': {action_message}")

            except Exception as e:
                error(f"Error processing transcription: {e}")

        self.shutdown()
