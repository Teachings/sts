import json
from helpers import log, load_config
from kafka import KafkaProducer

def invoke_after_transcription(json_output):
    """
    This function will be called after each transcription.
    You can define the actual implementation here.
    For now, let's just log the output.
    """
    log("Post-processing transcription", level="INFO")
    # log(f"{json.dumps(json_output, indent=4)}", level="INFO")
    # Assuming data is already validated and correct
    last_transcription = json_output['transcriptions'][-1]
    # print(f"Last transcription timestamp: {last_transcription['timestamp']}")
    log(f"{last_transcription['text']}", level="INFO", color="yellow")
    produce_message(last_transcription['text'])


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
        producer.send(TOPIC_NAME, value=message.encode("utf-8"))
        log(f"Message sent to topic '{TOPIC_NAME}': {message}", level="INFO", color="green")
    except Exception as e:
        log(f"Failed to send message to topic '{TOPIC_NAME}': {message}", level="ERROR", color="red")
    finally:
        producer.close()