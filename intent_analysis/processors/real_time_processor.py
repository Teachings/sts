from core.base_processor import BaseKafkaProcessor
from core.logger import info, debug, error
from agents.decision_agent import DecisionAgent

class RealTimeProcessor(BaseKafkaProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        self.consumer_group_id = kafka_config["consumer_groups"]["real_time"]

        self.input_topic = kafka_config["transcriptions_topic"]
        self.output_topic = kafka_config["actions_topic"]

        self.init_consumer(self.input_topic)
        self.init_producer()

        self.decision_agent = DecisionAgent(config)

    def process_records(self):
        info(f"RealTimeProcessor: Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            transcription = message.value
            debug(f"RealTimeProcessor received: {transcription}")

            try:
                # Use DecisionAgent or simplified logic to decide if it's urgent:
                decision = self.decision_agent.evaluate_transcription(transcription)

                if decision.action_required_decision:
                    action_msg = {
                        "original_text": transcription,
                        "reasoning": decision.reasoning,
                        "categorization": decision.categorization,
                        "refined_prompt": decision.refined_prompt
                    }
                    self.producer.send(self.output_topic, action_msg)
                    info(f"RealTimeProcessor: Action published: {action_msg}")
            except Exception as e:
                error(f"RealTimeProcessor Error: {e}")

        self.shutdown()
