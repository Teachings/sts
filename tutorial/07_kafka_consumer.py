import requests
import pydub
from pydub.playback import play
from kafka import KafkaConsumer

# Kafka configurations
TOPIC_NAME = "text_to_speech"
BROKER = "localhost:9092"

def consume_messages():
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=BROKER,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="text_to_speech_group",
        value_deserializer=lambda x: x.decode("utf-8")
    )

    print(f"Listening to topic '{TOPIC_NAME}'...")
    for message in consumer:
        print(f"Received message: {message.value}")

if __name__ == "__main__":
    consume_messages()
