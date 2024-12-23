# processors/real_time_processor.py

import json
from core.base_processor import BaseKafkaProcessor
from core.logger import info, debug, error
from agents.realtime_agent import RealtimeAgent
from agents.session_management_agent import SessionManagementAgent
from core.database import Database

class RealTimeProcessor(BaseKafkaProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_config = config["kafka"]
        db_config = config["db"]

        self.consumer_group_id = kafka_config["consumer_groups"]["real_time"]
        self.input_topic = kafka_config["transcriptions_topic"]
        self.output_topic = kafka_config["actions_topic"]
        self.session_mgmt_topic = kafka_config["sessions_management_topic"]

        self.init_consumer(self.input_topic)
        self.init_producer()

        # Agents
        self.realtime_agent = RealtimeAgent(config)
        self.session_agent = SessionManagementAgent(config)

        # DB if you want to check sessions in real-time (optional)
        self.db = Database(db_config)

    def process_records(self):
        info(f"RealTimeProcessor: Listening on topic '{self.input_topic}'...")
        for message in self.consumer:
            if not self.running:
                break

            raw_str = message.value
            debug(f"RealTimeProcessor received: {raw_str}")

            try:
                payload = json.loads(raw_str)
                text = payload.get("text", "")
                user_id = payload.get("user", "UnknownUser")

                # 1) Immediate action check
                decision = self.realtime_agent.evaluate_transcription(text)
                debug(f"RealTime Decision: {decision.model_dump()}")

                if decision.action_required_decision:
                    action_msg = {
                        "original_text": text,
                        "reasoning": decision.reasoning,
                        "categorization": decision.categorization,
                        "refined_prompt": decision.refined_prompt,
                        "user_id": user_id
                    }
                    self.producer.send(self.output_topic, action_msg)
                    info(f"RealTimeProcessor: Action published to {self.output_topic}")

                # 2) Session management check
                # Check DB if user has an active session
                active_sess = self.db.fetchone("""
                    SELECT id FROM sessions
                    WHERE user_id = %s AND active = TRUE
                    ORDER BY id DESC LIMIT 1
                """, (user_id,))
                has_active_session = bool(active_sess)

                session_decision_obj = self.session_agent.evaluate_session_decision(
                    user_text=text,
                    has_active_session=has_active_session
                )
                debug(f"Session Decision: {session_decision_obj.model_dump()}")

                # If the session agent decides CREATE or DESTROY, produce to sessions_management_topic
                if session_decision_obj.session_decision in ("CREATE", "DESTROY"):
                    msg_for_session_processor = {
                        "session_decision": session_decision_obj.session_decision,
                        "reasoning": session_decision_obj.reasoning,
                        "user_id": user_id
                    }
                    self.producer.send(self.session_mgmt_topic, msg_for_session_processor)
                    info(f"RealTimeProcessor: Session event published: {msg_for_session_processor}")

                # If NO_ACTION, do nothing regarding session

            except Exception as e:
                error(f"RealTimeProcessor Error: {e}")

        self.shutdown()
