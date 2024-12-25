import json
from helpers import log, load_config
from kafka import KafkaProducer
from models import TranscriptionSegment

def invoke_after_transcription(latest_transcription: TranscriptionSegment):
    """
    Processes the latest transcription segment and publishes it to Kafka.
    """
    log("Post-processing transcription", level="INFO")

    # Prepare the transcription data to send
    transcription_data = {
        "timestamp": latest_transcription.timestamp,
        "text": latest_transcription.text,
        "user": latest_transcription.user
    }

    # Log and produce the message
    log(f"Publishing transcription: {transcription_data['text']}", level="INFO", color="yellow")
    produce_message(transcription_data)


def produce_message(message):

    config = load_config()
    BROKER = config.get("broker", [])
    TOPIC_NAME = config.get("topic_transcriptions_all", [])

    # Kafka Configuration
    # BROKER = "localhost:9092"  # Replace with your broker's address if not localhost
    # TOPIC_NAME = "text_to_speech"
    # Initialize Kafka Producer
    producer = KafkaProducer(bootstrap_servers=BROKER)   
    try:
        # Send message to the topic
        producer.send(TOPIC_NAME, value=json.dumps(message).encode("utf-8"))
        log(f"Message sent to topic '{TOPIC_NAME}': {message}", level="INFO", color="green")
    except Exception as e:
        log(f"Failed to send message to topic '{TOPIC_NAME}': {message}", level="ERROR", color="red")
    finally:
        producer.close()