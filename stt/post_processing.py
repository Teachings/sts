from pydantic import ValidationError
from typing import Optional
from confluent_kafka.avro import AvroProducer
from confluent_kafka.avro import load as avro_load
from helpers import log, load_config
from models import TranscriptionSegment

def invoke_after_transcription(latest_transcription: TranscriptionSegment):
    """
    Processes the latest transcription segment and publishes it to Kafka using Avro.
    """
    log("Post-processing transcription", level="INFO")

    try:
        # Validate and prepare the transcription data
        transcription_data = latest_transcription.model_dump()

        # Log and produce the message
        log(f"Publishing transcription: {transcription_data['text']}",
            level="INFO", color="yellow")
        produce_message(transcription_data)

    except ValidationError as e:
        log(f"Validation error: {e}", level="ERROR")

def produce_message(message_dict):
    config = load_config()
    BROKER = config["kafka"]["broker"]
    TOPIC_NAME = config["kafka"]["topic_transcriptions_all"]
    SCHEMA_LOCATION = config["kafka"]["schema_location"]

    # Load the Avro schema
    value_schema = avro_load(SCHEMA_LOCATION)

    try:
        # Create AvroProducer
        avro_producer = AvroProducer(
            {
                "bootstrap.servers": BROKER,
                "schema.registry.url": config["kafka"]["schema_registry_url"]
            },
            default_value_schema=value_schema
        )
    except Exception as e:
        log(f"Failed to create Avro producer: {e}", level="ERROR", color="red")
        return  # Exit the function if producer creation fails
    else:
        try:
            # Produce Avro message
            avro_producer.produce(topic=TOPIC_NAME, value=message_dict)
            avro_producer.flush()

            log(f"Avro message sent to topic '{TOPIC_NAME}': {message_dict}",
                level="INFO", color="green")
        except Exception as e:
            log(f"Failed to send Avro message: {e}", level="ERROR", color="red")