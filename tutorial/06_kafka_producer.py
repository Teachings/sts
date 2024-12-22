from kafka import KafkaProducer

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

if __name__ == "__main__":
    while True:
        message = input("Enter a message to send to Kafka (or 'exit' to quit): ")
        if message.lower() == 'exit':
            break
        produce_message(message)
