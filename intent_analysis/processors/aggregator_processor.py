from confluent_kafka import KafkaException
from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, error
from core.database import Database
from agents.aggregator_agent import AggregatorAgent

class AggregatorProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]
        db_cfg = config["db"]

        self.input_topic = kafka_cfg["aggregations_request_topic"]
        group_id = kafka_cfg["consumer_groups"]["aggregator"]

        self.db = Database(db_cfg)
        self.aggregator_agent = AggregatorAgent(config)

        # Only Avro consumer for aggregator requests
        self.init_consumer(group_id=group_id, topics=[self.input_topic], offset_reset="latest")

    def process_records(self):
        info(f"AggregatorProcessor: Listening on topic '{self.input_topic}' (Avro)...")

        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    error(f"AggregatorProcessor consumer error: {msg.error()}")
                    continue

                data = msg.value()
                if not data:
                    continue

                session_id = data.get("session_id")
                user_id = data.get("user_id")

                # 1. Retrieve session timestamps
                session_sql = """
                    SELECT start_time, end_time FROM sessions
                    WHERE id = %s
                """
                session_row = self.db.fetchone(session_sql, (session_id,))
                if not session_row:
                    error(f"AggregatorProcessor: No session found with id {session_id}")
                    continue

                start_time = session_row["start_time"]
                end_time = session_row["end_time"]
                info(f"Start Time: {start_time}, end Time: {end_time} for session {session_id}")

                # 2. Gather transcriptions using start and end timestams only (do not use session_id here)
                select_transcriptions_sql = """
                    SELECT text FROM transcriptions
                    WHERE timestamp BETWEEN %s AND %s AND user_id = %s
                    ORDER BY id
                """
                rows = self.db.fetchall(select_transcriptions_sql, (start_time, end_time, user_id))
                all_text = [r["text"] for r in rows]

                # 3. Aggregate text
                aggregated_text = "\n".join(all_text)
                info(f"AggregatorProcessor: Aggregated {len(all_text)} transcriptions for session {session_id}")

                # 4. Analyze and aggregate with the AggregatorAgent
                aggregation_result = self.aggregator_agent.analyze_and_aggregate_text(aggregated_text)

                # 5. Store in session summary
                update_session_sql = """
                    UPDATE sessions
                    SET summary = %s,
                        ai_organized_text = %s,
                        ai_summary = %s
                    WHERE id = %s
                """
                self.db.execute(update_session_sql, (
                    aggregated_text,
                    aggregation_result.organized_text,
                    aggregation_result.summary,
                    session_id
                ))
                info(f"AggregatorProcessor: Stored organized text and summary in session {session_id}")

            except KafkaException as ke:
                error(f"Kafka error in AggregatorProcessor: {ke}")
            except Exception as e:
                error(f"AggregatorProcessor Error: {e}")

        self.shutdown()