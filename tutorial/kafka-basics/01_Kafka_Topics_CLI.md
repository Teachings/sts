# Kafka Topics CLI Tutorial

This tutorial provides step-by-step instructions on how to create, delete, describe, or change a Kafka topic using Kafka Topics CLI. Ensure that Kafka is running before you execute any commands.

## CLI Extensions
Use the appropriate CLI commands for Linux:
- **Linux**: `kafka-topics.sh`

---

## How to Create a Kafka Topic
To create a Kafka topic, you need to provide these mandatory parameters:
1. Topic name
2. Number of partitions
3. Replication factor

### Command for Kafka v2.2+
For Kafka version 2.2 and above, use the `--bootstrap-server` option:
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --topic text_to_speech --create --partitions 3 --replication-factor 1
```

### Additional Notes
- Avoid using the Zookeeper option as it is deprecated and removed in Kafka v3.
- Topics with periods (`.`) or underscores (`_`) in their names might collide in metric names. Use one naming convention consistently.

---

## How to List Kafka Topics
To list all Kafka topics:

### Command for Kafka v2.2+
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Additional Notes
- Internal topics (e.g., `__consumer_offsets`) are listed by default. Use `--exclude-internal` to hide them if needed.

---

## How to Describe a Kafka Topic
To get details about a Kafka topic:

### Command for Kafka v2.2+
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic text_to_speech
```

### Additional Notes
- Details include partition count, replication factor, leaders, and in-sync replicas (ISR).
- To describe multiple topics, provide a comma-delimited list of topic names.

---

## How to Increase the Number of Partitions
To increase the number of partitions in a Kafka topic:

### Command for Kafka v2.2+
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --alter --topic text_to_speech --partitions 5
```

### Important
- Be cautious when increasing partitions if applications rely on key-based ordering. Create a new topic and redistribute data if necessary.

---

## How to Delete a Kafka Topic
To delete a Kafka topic:

### Command for Kafka v2.2+
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic text_to_speech
```

### Additional Notes
- Ensure the `delete.topic.enable=true` setting is configured in the broker.
- Deleting a topic might take time; verify the operation with a `--describe` command afterward.

---

## Advanced Options
- **Set topic configurations**: `--config max.message.bytes=64000`
- **Filter partitions**: Use options like `--at-min-isr-partitions`, `--unavailable-partitions`, `--under-replicated-partitions`
- **Exclude internal topics**: `--exclude-internal`

---

This guide provides the essential commands and practices for managing Kafka topics efficiently using Kafka Topics CLI on Linux.