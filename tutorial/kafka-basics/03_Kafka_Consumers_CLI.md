# Kafka Consumer CLI Tutorial

This tutorial provides instructions on how to consume data from Kafka using the Kafka Console Consumer CLI. Ensure that Kafka is running before you execute any commands.

## CLI Extensions
Use the appropriate CLI commands for Linux:
- **Linux**: `kafka-console-consumer.sh`

---

## How to Consume Data in a Kafka Topic
To consume data from a Kafka topic, provide the following mandatory parameters:
1. Kafka hostname and port (e.g., localhost:9092)
2. Topic name

### Consuming Only Future Messages
To consume only future messages:
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech
```

### Consuming All Historical and Future Messages
To consume all messages from the beginning:
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech --from-beginning
```

To exit the Kafka console consumer, press `Ctrl+C`.

### Additional Notes
- The console consumer assumes all messages can be deserialized as text.
- If no output appears but the topic has data, use the `--from-beginning` option.

---

## How to Consume a Kafka Topic and Show Both Key and Value
By default, the console consumer shows only the value of Kafka records. Use the following command to display both key and value:

### Command Example
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech --formatter kafka.tools.DefaultMessageFormatter --property print.timestamp=true --property print.key=true --property print.value=true --from-beginning
```

### Output Example
```text
CreateTime:1641810588071	null	hello
CreateTime:1641823304170	name	Kafka
CreateTime:1641823301294	example_key	example_value
```

---

## Advanced Options
- **Historical Messages**: Use `--from-beginning` to read all previous messages.
- **Custom Formatting**: Use the `--formatter` option to display keys, timestamps, and other metadata.
- **Custom Consumer Properties**: Use `--consumer-property` to set properties like `allow.auto.create.topics`.
- **Consumer Groups**: Specify a consumer group ID with `--group`. By default, a random group ID is generated.
- **Specific Partitions**: Use `--partition` to consume messages from a specific partition.
- **Maximum Messages**: Limit consumption to a specific number of messages using `--max-messages`.

---

## Kafka Consumers in Group CLI Tutorial

Use the appropriate CLI commands for Linux:
- **Linux**: `kafka-console-consumer.sh`

In addition, we will provide an optional consumer group parameter with the `--group` flag.

---

### How to Create Consumers in a Kafka Consumer Group
To start consumers in a consumer group, follow these steps:

1. **Create a topic with at least 2 partitions and send data to it:**
   ```bash
   kafka-topics.sh --bootstrap-server localhost:9092 --topic text_to_speech --create --partitions 3 --replication-factor 1
   ```

2. **Launch the first consumer in a consumer group, named `my-first-application`:**
   ```bash
   kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech --group my-first-application
   ```

3. **Open a new terminal and launch a second consumer in the same group:**
   ```bash
   kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech --group my-first-application
   ```

4. **Launch a third consumer in the same group:**
   ```bash
   kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech --group my-first-application
   ```

Each consumer in the group will get assigned a partition. Produce a few string messages to the topic:
```bash
kafka-console-producer.sh --bootstrap-server localhost:9092 --topic text_to_speech
>first message
>second message
>third message
>fourth message
```
Each consumer will show only the messages produced on the partition assigned to it.

If a consumer stops, messages automatically get reassigned to the remaining consumers, as the group performs a rebalance. When consumers restart, they resume from the latest committed offsets.

### Example Output After Restart
```bash
kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic text_to_speech --group my-first-application
>eighth message
>ninth message
>tenth message
```

---

### Notes
- If you consume in a group and later use `--from-beginning`, the option is ignored unless the consumer group is reset.
- Without specifying `--group`, a random consumer group ID is generated.
- Verify topic partitions using the `kafka-topics --describe` command if one consumer seems to handle all messages.