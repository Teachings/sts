import json
from pydantic import ValidationError
from helpers import log, load_config
from kafka import KafkaProducer
from models import TranscriptionSegment

def invoke_after_transcription(latest_transcription: TranscriptionSegment):
    """
    Processes the latest transcription segment and publishes it to Kafka.
    """
    log("Post-processing transcription", level="INFO")

    try:
        # Validate and prepare the transcription data to send
        transcription_data = latest_transcription.model_dump()
        
        # Log and produce the message
        log(f"Publishing transcription: {transcription_data['text']}", level="INFO", color="yellow")
        produce_message(transcription_data)
    
    except ValidationError as e:
        log(f"Validation error: {e}", level="ERROR")

def produce_message(message):

    config = load_config()
    BROKER = config.get("broker", [])
    TOPIC_NAME = config.get("topic_transcriptions_all", [])

    # Initialize Kafka Producer
    try:
        # Create Kafka producer
        producer = KafkaProducer(bootstrap_servers=BROKER)
    except Exception as e:
        log(f"Failed to create Kafka producer: {e}", level="ERROR", color="red")
    else:
        try:
            # Send message to the topic
            producer.send(TOPIC_NAME, value=json.dumps(message).encode("utf-8"))
            log(f"Message sent to topic '{TOPIC_NAME}': {message}", level="INFO", color="green")
        except Exception as e:
            log(f"Failed to send message to topic '{TOPIC_NAME}': {message}. Error: {e}", level="ERROR", color="red")
        finally:
            producer.close()