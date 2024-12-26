# Kafka Consumer Group Management CLI Tutorial

This tutorial provides instructions for managing consumer groups in Kafka using the Kafka Consumer Groups CLI (`kafka-consumer-groups`). Ensure that Kafka is running before executing any commands.

## CLI Extensions
Use the appropriate CLI commands for Linux:
- **Linux**: `kafka-consumer-groups.sh`

---

## How to Reset a Kafka Consumer Group
To reset Kafka consumer groups, follow these steps:

1. **Find your broker hostname and port** (e.g., `localhost:9092`).
2. **Understand the offset reset strategy** (e.g., to earliest, to latest, to a specific offset, or shift by a value).
3. **Stop the running consumer groups** (otherwise, the reset command will fail).
4. **Use the `--reset-offsets` option** with the Kafka Consumer Groups CLI.

### Reset Offsets to the Earliest
First, ensure that consumers in the group are stopped:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group my-first-application
```
Output:
```text
Consumer group 'my-first-application' has no active members.
```

Observe the current offsets for the consumer group:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group my-first-application
```
Output:
```text
GROUP                TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
my-first-application text_to_speech  0          3               3               0
my-first-application text_to_speech  1          5               5               0
my-first-application text_to_speech  2          6               6               0
```

Reset the offsets to the earliest position:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group my-first-application --reset-offsets --to-earliest --execute --topic text_to_speech
```
Output:
```text
GROUP                TOPIC           PARTITION  NEW-OFFSET
my-first-application text_to_speech  0          0
my-first-application text_to_speech  1          0
my-first-application text_to_speech  2          0
```
Restarting a consumer in the group will now read from the beginning of each partition.

### Reset Offsets by Shifting
Stop the running consumers and observe current offsets:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group my-first-application
```
Reset offsets by shifting by `-2`:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group my-first-application --reset-offsets --shift-by -2 --execute --topic text_to_speech
```
Output:
```text
GROUP                TOPIC           PARTITION  NEW-OFFSET
my-first-application text_to_speech  0          1
my-first-application text_to_speech  1          3
my-first-application text_to_speech  2          4
```
Messages will now start from the adjusted offsets.

---

## Listing Kafka Consumers in a Consumer Group
To list all Kafka consumers in a group:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group my-first-application
```
Output:
```text
GROUP                TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG             CONSUMER-ID
my-first-application text_to_speech  0          3               3               0               consumer-id-1
my-first-application text_to_speech  1          5               5               0               consumer-id-2
my-first-application text_to_speech  2          6               6               0               consumer-id-3
```
Descriptions include:
- **CONSUMER ID**: Unique identifier of the consumer to the Kafka broker.
- **CURRENT-OFFSET**: The latest committed offset for the group.
- **LAG**: How far behind a consumer is to the end of the topic.

---

## Listing All Kafka Consumer Groups
To list all consumer groups:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list --state
```
Output:
```text
GROUP                STATE
my-first-application Stable
```

Describe all consumer groups and their states:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --all-groups --state
```
Output:
```text
GROUP                     COORDINATOR (ID)          ASSIGNMENT-STRATEGY  STATE           #MEMBERS
my-first-application      127.0.0.1:9092 (1)        range                Stable          3
```

---

## Deleting a Kafka Consumer Group
To delete a consumer group:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --delete --group my-first-application
```
Output:
```text
Deletion of requested consumer groups ('my-first-application') was successful.
```

Alternatively, delete offsets for a specific topic:
```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --delete-offsets --group my-first-application --topic text_to_speech
```
Output:
```text
TOPIC                          PARTITION       STATUS
text_to_speech                 0               Successful
text_to_speech                 1               Successful
text_to_speech                 2               Successful
```