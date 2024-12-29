from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, debug, error
from agents.realtime_agent import RealtimeAgent
from agents.session_management_agent import SessionManagementAgent
from core.database import Database

class RealTimeProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]
        db_cfg = config["db"]

        self.input_topic = kafka_cfg["transcriptions_topic"]
        group_id = kafka_cfg["consumer_groups"]["real_time"]

        self.output_topic_actions = kafka_cfg["actions_topic"]
        self.output_topic_sessions = kafka_cfg["sessions_management_topic"]

        # Avro consumer for transcription
        self.init_consumer(group_id=group_id, topics=[self.input_topic], offset_reset="latest")

        # Avro producer for action messages
        self.init_producer(
            producer_name="action_producer",
            avro_schema_file="schemas/action_value.avsc"
        )
        # Avro producer for session mgmt messages
        self.init_producer(
            producer_name="session_mgmt_producer",
            avro_schema_file="schemas/session_mgmt_value.avsc"
        )

        self.realtime_agent = RealtimeAgent(config)
        self.session_agent = SessionManagementAgent(config)
        self.db = Database(db_cfg)

    def process_records(self):
        info(f"RealTimeProcessor: Listening on {self.input_topic} (Avro)...")

        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    error(f"RealTimeProcessor consumer error: {msg.error()}")
                    continue

                payload = msg.value()
                if not payload:
                    continue
                
                text = payload.get("text", "")
                user_id = payload.get("user", "UnknownUser")
                timestamp = payload.get("timestamp", "")

                # 1) Immediate action check
                decision = self.realtime_agent.evaluate_transcription(text)
                debug(f"RealTime Decision: {decision.model_dump()}")

                if decision.action_required_decision:
                    action_msg = {
                        "original_text": text,
                        "reasoning": decision.reasoning,
                        "categorization": decision.categorization,
                        "refined_prompt": decision.refined_prompt,
                        "user_id": user_id,
                        "timestamp": timestamp
                    }
                    self.produce_message(
                        producer_name="action_producer",
                        topic_name=self.output_topic_actions,
                        value_dict=action_msg
                    )
                    info(f"RealTimeProcessor: Published action to {self.output_topic_actions}")

                # 2) Session management check
                active_session = self.db.fetchone("""
                    SELECT id FROM sessions
                    WHERE user_id = %s AND active = TRUE
                    ORDER BY id DESC LIMIT 1
                """, (user_id,))

                if not active_session:
                    # No active session, request creation of a new session
                    session_msg = {
                        "session_decision": "CREATE",
                        "reasoning": "No active session found.",
                        "user_id": user_id,
                        "timestamp": timestamp
                    }
                    self.produce_message(
                        producer_name="session_mgmt_producer",
                        topic_name=self.output_topic_sessions,
                        value_dict=session_msg
                    )
                    info(f"RealTimeProcessor: Published session create request to {self.output_topic_sessions}")
                else:
                    # Active session exists, check with SessionManagementAgent if it should be closed
                    session_decision_obj = self.session_agent.evaluate_session_decision(text)
                    debug(f"Session Decision: {session_decision_obj.model_dump()}")

                    if session_decision_obj.destroy_decision:
                        session_msg = {
                            "session_decision": "DESTROY", # Using string for consistency with original design
                            "reasoning": session_decision_obj.reasoning,
                            "user_id": user_id,
                            "timestamp": timestamp
                        }
                        self.produce_message(
                            producer_name="session_mgmt_producer",
                            topic_name=self.output_topic_sessions,
                            value_dict=session_msg
                        )
                        info(f"RealTimeProcessor: Published session destroy request to {self.output_topic_sessions}")

            except Exception as e:
                error(f"RealTimeProcessor Error: {e}")

        self.shutdown()