# Kafka Producer CLI Tutorial

This tutorial provides instructions on how to send data into Kafka using the Kafka Console Producer CLI. Ensure that Kafka is running before you execute any commands.

## CLI Extensions
Use the appropriate CLI commands for Linux:
- **Linux**: `kafka-console-producer.sh`

---

## How to Produce a Message into a Kafka Topic
To send data to a Kafka topic, provide the following mandatory parameters:
1. Kafka hostname and port (e.g., localhost:9092)
2. Topic name

### Command for Kafka v2.5+
For Kafka version 2.5 and above, use the `--bootstrap-server` option:
```bash
kafka-console-producer.sh --bootstrap-server localhost:9092 --topic text_to_speech
```

To exit the Kafka console producer, press `Ctrl+C`.

### Additional Notes
- If the specified topic does not exist, Kafka can automatically create it based on default broker-side settings. Ensure these settings meet your requirements.

---

## How to Produce Messages from a File
To produce messages from a file, ensure each message is on a new line within the file.

### Example Command
Assume the file `topic-input.txt` contains the following lines:
```text
Hello World
My name is Kafka
```
Produce messages from the file using the following command:
```bash
kafka-console-producer.sh --bootstrap-server localhost:9092 --topic text_to_speech < topic-input.txt
```

---

## How to Produce Messages with a Key
By default, messages are sent with a null key. To include keys:
1. Use `--property parse.key=true`.
2. Define a key-value separator using `--property key.separator`.

### Command Example
Using `:` as the key-value separator:
```bash
kafka-console-producer.sh --bootstrap-server localhost:9092 --topic text_to_speech --property parse.key=true --property key.separator=:
```

### Input Example
Provide input in the following format:
```text
example_key:example_value
name:Kafka
```
Ensure the separator is consistently used; otherwise, an exception will occur.

---

## Advanced Options
- **Message Compression**: Use the `--compression-codec` option with values such as `gzip`, `snappy`, `lz4`, or `zstd`.
- **Custom Producer Properties**: Use `--producer-property` to pass specific producer properties, e.g., `acks=all`.

---

This guide covers essential commands and practices for using Kafka Console Producer CLI on Linux.