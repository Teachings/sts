from kafka import KafkaConsumer
from pydantic import BaseModel, Field, ValidationError
import json

# Kafka configurations
TOPIC_NAME = "text_to_speech"
BROKER = "localhost:9092"

# Pydantic model for deserializing messages
class TranscriptionSegment(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the transcription")
    text: str = Field(..., description="Text of the transcription")
    user: str = Field(..., description="User Id")

def consume_messages():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BROKER,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id="text_to_speech_group",
        value_deserializer=lambda x: x.decode("utf-8")
    )

    print(f"Listening to topic '{TOPIC_NAME}'...")
    for message in consumer:
        try:
            # Deserialize the message value (JSON string) into a Pydantic object
            data = TranscriptionSegment(**json.loads(message.value))
            print(f"Received TranscriptionSegment: {data}")
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")
        except ValidationError as e:
            print(f"Validation error: {e}")

if __name__ == "__main__":
    consume_messages()
