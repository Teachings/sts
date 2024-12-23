from datetime import datetime
from kafka import KafkaProducer
from pydantic import BaseModel, Field
from typing import List

class TranscriptionSegment(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the transcription")
    text: str = Field(..., description="Text of the transcription")
    user: str = Field(..., description="User Id")

# Kafka Configuration
BROKER = "localhost:9092"  # Replace with your broker's address if not localhost
TOPIC_NAME = "transcriptions.all"

def produce_message(message):
    # Initialize Kafka Producer
    producer = KafkaProducer(bootstrap_servers=BROKER)
    # Send message to the topic
    producer.send(TOPIC_NAME, value=message.encode("utf-8"))
    producer.close()
    print(f"Message sent to topic '{TOPIC_NAME}': {message}")

def generate_json(current_transcription: TranscriptionSegment):
    """
    Generates the updated JSON structure after every transcription.
    This is where data is ready to be sent downstream or saved if required.
    """
    json_output = {
        "timestamp": current_transcription.timestamp,
        "text": current_transcription.text,
        "user": current_transcription.user
    }
    return json_output

if __name__ == "__main__":
    while True:
        message = input("Enter a message to send to Kafka (or 'exit' to quit): ")
        if message.lower() == 'exit':
            break
        transcription_segment = TranscriptionSegment(
            timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
            text=message, 
            user="mukul"
            )
        produce_message(transcription_segment.model_dump_json())
