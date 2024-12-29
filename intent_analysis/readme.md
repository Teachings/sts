# STS Application - Kafka + Avro Architecture

## Overview

This Kafka-based application is designed to be decoupled, modular, and extensible:

- **Multiple processors** (e.g. `RealTimeProcessor`, `PersistenceProcessor`, `SessionProcessor`, etc.) demonstrate the flow from **incoming Avro messages** to **database writes**, **LLM-based decisions**, and **final TTS** or **aggregated summaries**.
- **Kafka** acts as the data fabric, passing messages between these independently running consumers/producers.
- **Agents** (like `RealtimeAgent`, `SessionManagementAgent`, or `DecisionAgent`) and **services** (like the TTS service) are each in their own modules, making them easy to replace, extend, or augment.
- **Adding a new processor** means creating a subclass of `BaseAvroProcessor` and hooking into the relevant Kafka topics.
- **Adding a new agent** means creating a new class in `agents/` and calling it from whichever processor(s) need that agent’s logic.

This document covers:

1.  **System Architecture and High-Level Flow**
2.  **Processor Concept** (Avro-based)
3.  **Key Processors** (RealTime, Session, Aggregator, Persistence, Intent, etc.)
4.  **Avro Schemas & Message Flow**
5.  **Steps to Add a New Processor** (with Avro)
6.  **Steps to Add a New Agent**
7.  **Appendix: Creating and Using Avro Schemas**

---

## 1. System Architecture Overview

### 1.1 Three Primary Layers

1.  **Core**
    -   Basic infrastructure and utilities, such as:
        -   **`config_loader.py`**: Loads YAML configuration (Kafka broker info, DB credentials, etc.).
        -   **`base_avro_processor.py`**: Our common base class for Avro-based Kafka processors.
        -   **`database.py`**: Database connectivity helpers (Postgres).
        -   **`logger.py`**: A simplified logger with colorized outputs.

2.  **Processors**
    -   **RealTimeProcessor**: Consumes transcriptions in real time, uses `RealtimeAgent` to decide if immediate action is needed. **It also ensures a session is always active by requesting a new session when one doesn't exist and checks with `SessionManagementAgent` to determine if an active session should be closed.**
    -   **SessionProcessor**: Listens for session creation/destruction requests, updates the DB, **implements session timeout logic**, and triggers the aggregator when sessions end.
    -   **AggregatorProcessor**: Gathers transcriptions within a session’s timeframe, aggregates them, and stores the result.
    -   **PersistenceProcessor**: Stores all incoming transcriptions into a Postgres table.
    -   **IntentProcessor**: Takes “action required” messages, calls TTS on the `reasoning` field, and plays the audio.
    -   **TranscriptionProcessor** (optional/legacy): Consumes from `transcriptions.all` and uses a simpler agent model (`DecisionAgent`).

3.  **Agents / Services**
    -   **RealtimeAgent**: Interacts with an LLM to determine if a user’s utterance requires immediate action (e.g., “turn off the lights”).
    -   **SessionManagementAgent**: An LLM-based agent that decides whether to **DESTROY** a session **based on explicit user requests**.
    -   **DecisionAgent**: An older or alternate agent that decides if an action is required for a given transcription.
    -   **TTS Service**: Connects to an external text-to-speech endpoint and plays the resulting audio.

### 1.2 High-Level Message Flow

1.  **Speech-to-Text** service publishes transcriptions as Avro messages to **`transcriptions.all`**.
2.  **PersistenceProcessor** consumes these Avro messages and writes them to Postgres for permanent storage.
3.  **RealTimeProcessor**:
    -   Consumes from `transcriptions.all`.
    -   Uses `RealtimeAgent` to see if immediate action is needed. If yes, it produces an Avro message to `transcriptions.agent.action`.
    -   **Checks for an active session. If none exists, it publishes a `CREATE` message to `sessions.management`. If a session exists, it calls `SessionManagementAgent` to see if we should destroy the session, publishing to `sessions.management` if necessary.**
4.  **SessionProcessor**:
    -   Consumes from `sessions.management`, updates the `sessions` table, **creating sessions when requested by `RealTimeProcessor`** and setting `active = FALSE` / `end_time` when the user says “destroy session” or when a session times out. **Sessions are automatically closed after a period of inactivity (timeout logic implemented in `SessionProcessor`).**
    -   Publishes an **aggregation request** (`aggregations.request`) when a session ends.
5.  **AggregatorProcessor**:
    -   Consumes from `aggregations.request`, queries all transcriptions in that session timeframe from the DB, aggregates them, and updates the `sessions.summary`.
6.  **IntentProcessor**:
    -   Consumes “action required” messages from `transcriptions.agent.action`, performs TTS on the `reasoning` field, and plays the audio.

All these processors are loosely coupled—they communicate only through Kafka topics with Avro messages.

---

## 2. Processor Concept (Avro)

Each **Processor** is a **class** that inherits from `BaseAvroProcessor`. This base class:

-   Sets up an **AvroConsumer** for reading Avro-serialized messages from Kafka.
-   Lets you initialize one or more **AvroProducer** instances if you also need to send Avro-serialized messages to another topic.
-   Handles signals (SIGINT, SIGTERM) for graceful shutdown.
-   Provides a `run()` method with a polling loop that calls `process_records()`.

### Typical Steps in a Processor

1.  In the constructor (`__init__`):
    -   Load config.
    -   Call `init_consumer(group_id, [list_of_topics])`.
    -   If you need to produce Avro messages to other topics, call `init_producer("producer_name", "schemas/some_schema.avsc")` for each schema.
2.  In `process_records()`:
    -   Poll for messages (`msg = self.consumer.poll(...)`).
    -   Handle any errors.
    -   Parse the Avro-deserialized dictionary from `msg.value()`.
    -   Use your logic or agent calls to decide what to do with the message.
    -   If you need to produce an Avro message, call:

        ```python
        self.produce_message(
          producer_name="some_producer",
          topic_name="some_topic",
          value_dict=your_avro_compatible_dict
        )
        ```

3.  `shutdown()` is automatically called on signals.

---

## 3. Key Processors in This Project

1.  **RealTimeProcessor**
    -   **Consumes**: `transcriptions.all` (schema: `transcription_value.avsc`)
    -   **Produces**: `transcriptions.agent.action` (schema: `action_value.avsc`) + `sessions.management` (schema: `session_mgmt_value.avsc`)

2.  **SessionProcessor**
    -   **Consumes**: `sessions.management` (schema: `session_mgmt_value.avsc`)
    -   **Produces**: `aggregations.request` (schema: `aggregator_value.avsc`)

3.  **AggregatorProcessor**
    -   **Consumes**: `aggregations.request` (schema: `aggregator_value.avsc`)
    -   **Produces**: none (just updates DB)

4.  **PersistenceProcessor**
    -   **Consumes**: `transcriptions.all` (schema: `transcription_value.avsc`)
    -   **Produces**: none (just inserts into DB)

5.  **IntentProcessor**
    -   **Consumes**: `transcriptions.agent.action` (schema: `action_value.avsc`)
    -   **Produces**: none (just calls TTS)

*(We also have an optional `TranscriptionProcessor` that consumes from `transcriptions.all` and publishes to `transcriptions.agent.action`, but it’s more legacy.)*

---

## 4. Avro Schemas & Message Flow

We store **Avro schemas** in the `schemas/` directory. For example:

1.  **`transcription_value.avsc`**

    ```json
    {
      "type": "record",
      "name": "TranscriptionSegment",
      "namespace": "sts.transcription",
      "fields": [
        { "name": "timestamp", "type": "string" },
        { "name": "text", "type": "string" },
        { "name": "user", "type": "string" }
      ]
    }
    ```

    -   Used on topic `transcriptions.all`.

2.  **`action_value.avsc`**

    ```json
    {
      "type": "record",
      "name": "ActionMessage",
      "namespace": "sts.action",
      "fields": [
        { "name": "original_text", "type": "string" },
        { "name": "reasoning", "type": "string" },
        { "name": "categorization", "type": ["null","string"], "default": null },
        { "name": "refined_prompt", "type": ["null","string"], "default": null },
        { "name": "user_id", "type": "string" },
        { "name": "timestamp", "type": "string" }
      ]
    }
    ```

    -   Used on topic `transcriptions.agent.action`.

3.  **`session_mgmt_value.avsc`**

    ```json
    {
      "type": "record",
      "name": "SessionMgmtMessage",
      "namespace": "sts.session",
      "fields": [
        { "name": "session_decision", "type": "string" },
        { "name": "reasoning", "type": "string" },
        { "name": "user_id", "type": "string" },
        { "name": "timestamp", "type": "string" }
      ]
    }
    ```

    -   Used on topic `sessions.management`.

4.  **`aggregator_value.avsc`**

    ```json
    {
      "type": "record",
      "name": "AggregatorRequest",
      "namespace": "sts.aggregator",
      "fields": [
        { "name": "session_id", "type": "int" },
        { "name": "user_id", "type": "string" }
      ]
    }
    ```

    -   Used on topic `aggregations.request`.

The **Confluent Schema Registry** is used to store these schemas. Our code uses **`confluent-kafka[avro]`** to automatically **register** or **fetch** schemas based on the topic when we produce/consume messages.

---

## 5. **Steps to Add a New Processor (Avro-Based)**

### 5.1 Create (or Reuse) an Avro Schema

If your new processor **consumes** from an existing topic, you can reuse that existing schema. If you produce to a **new** topic, create a new `.avsc` file in `schemas/`, specifying your record fields and the `namespace`.

> **Example**: Suppose we want a new processor named **`TopicAnalysisProcessor`** that:
> - Consumes from `transcriptions.all` (using `transcription_value.avsc`).  
> - Produces to `analysis.output` (with a new Avro schema, e.g. `analysis_value.avsc`).

**analysis_value.avsc** might look like:
```json
{
  "type": "record",
  "name": "AnalysisResult",
  "namespace": "sts.analysis",
  "fields": [
    { "name": "user_id", "type": "string" },
    { "name": "analysis_text", "type": "string" },
    { "name": "timestamp", "type": "string" }
  ]
}
```

### 5.2 Create Your Processor File

```python
# File: processors/topic_analysis_processor.py

from confluent_kafka import KafkaException
from core.base_avro_processor import BaseAvroProcessor
from core.logger import info, debug, error

class TopicAnalysisProcessor(BaseAvroProcessor):
    def __init__(self, config):
        super().__init__(config)
        kafka_cfg = config["kafka"]

        # Consumer setup
        self.input_topic = kafka_cfg["transcriptions_topic"]  # e.g. "transcriptions.all"
        group_id = "topic_analysis_consumer_group"  # or from config

        self.init_consumer(group_id=group_id, topics=[self.input_topic], offset_reset="latest")

        # Producer setup for new analysis output topic
        self.output_topic = "analysis.output"
        self.init_producer(
            producer_name="analysis_producer",
            avro_schema_file="schemas/analysis_value.avsc"
        )

    def process_records(self):
        info(f"TopicAnalysisProcessor: Listening on {self.input_topic}...")
        while self.running:
            try:
                msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    error(f"TopicAnalysisProcessor consumer error: {msg.error()}")
                    continue

                # Avro-deserialized dict
                payload = msg.value()
                if not payload:
                    continue

                # e.g. payload = { "timestamp": "...", "text": "...", "user": "..." }
                text = payload.get("text", "")
                user_id = payload.get("user", "UnknownUser")
                timestamp = payload.get("timestamp", "")

                # Custom analysis logic
                analysis_result = do_analysis(text)

                # Build Avro-compatible output
                analysis_avro = {
                    "user_id": user_id,
                    "analysis_text": analysis_result,
                    "timestamp": timestamp
                }

                # Produce to analysis.output
                self.produce_message(
                    producer_name="analysis_producer",
                    topic_name=self.output_topic,
                    value_dict=analysis_avro
                )

            except KafkaException as ke:
                error(f"Kafka error in TopicAnalysisProcessor: {ke}")
            except Exception as e:
                error(f"TopicAnalysisProcessor error: {e}")

        self.shutdown()

def do_analysis(text: str) -> str:
    # ... your custom logic ...
    return f"Analyzed: {text}"
```

### 5.3 Add a Run Script

```python
# File: run_topic_analysis_processor.py

from core.config_loader import load_config
from processors.topic_analysis_processor import TopicAnalysisProcessor
from core.logger import error

if __name__ == "__main__":
    try:
        config = load_config()
        processor = TopicAnalysisProcessor(config)
        processor.run()
    except Exception as e:
        error(f"Failed to start TopicAnalysisProcessor: {e}")
```

### 5.4 Reference the New Topic(s) in `config.yml` (Optional)

Add or update references:

```yaml
kafka:
  broker: "localhost:9092"
  transcriptions_topic: "transcriptions.all"
  # ...
  analysis_output_topic: "analysis.output"
```

Then in your processor, you can read from `config["kafka"]["analysis_output_topic"]` if you prefer.

### 5.5 Run the Processor

```bash
python run_topic_analysis_processor.py
```

The first time it **produces** a message with the `analysis_value.avsc` schema, that schema is registered in your Schema Registry. The consumer logic (if another microservice or processor is to read from `analysis.output`) must also set up Avro to decode it.

---

## 6. **Steps to Add a New Agent**

1. **Create a file** in `agents/`, e.g. `my_custom_agent.py`.  
2. **Define** a Pydantic model for the agent’s input/output.  
3. **Implement** the logic that calls your LLM or other service.  
4. **Modify** whichever processor(s) should call this agent. For example:
   ```python
   from agents.my_custom_agent import MyCustomAgent

   class SomeProcessor(BaseAvroProcessor):
       ...
       def process_records(self):
           msg = self.consumer.poll(1.0)
           ...
           # Use the agent
           agent = MyCustomAgent(...)
           result = agent.do_stuff(input_text)
           ...
   ```
5. Make sure you handle the agent’s return structure in your produce or DB insertion logic, if needed.

---

## 7. **Appendix: Creating & Using Avro Schemas**

### 7.1 Why Avro?

- Avro enforces a **consistent message format** across producers/consumers.  
- The **Confluent Schema Registry** ensures version control and compatibility rules (backward, forward, full).  
- Avro-serialized messages are more compact than JSON and can be strongly typed.

### 7.2 Typical Workflow

1. **Write** your `.avsc` schema with `type="record"`, `name="YourMessage"`, a **namespace** (e.g. `sts.something`), and a `fields` array.  
2. **Place** it in the `schemas/` directory.  
3. **Load** it at runtime using `from confluent_kafka.avro import load as avro_load`.  
4. **Create** an `AvroProducer` with the loaded schema.  
5. **Produce** Avro messages (dictionaries) that match the schema fields.  
6. **Consume** Avro messages with an `AvroConsumer`, which automatically fetches the schema from the registry and converts messages to Python dictionaries.

### 7.3 Handling Evolving Schemas

- If you need to **add a field** or **change types**, consider Avro compatibility rules (e.g. adding a field with a default is typically backward-compatible).  
- Bump your schema version if making non-compatible changes.

---

## **Conclusion**

With **`BaseAvroProcessor`**, **all** of our processors:

- **Consume** Avro messages from one (or more) input topics via `AvroConsumer`.  
- **Optionally produce** Avro messages to other topics via one or multiple `AvroProducer` instances.  
- Operate in a **loosely coupled** system, communicating only through Kafka topics.  
- Leverage **Confluent Schema Registry** for typed, versioned message formats.

**Key Points**:

- Keep **processors** small and focused (e.g. handle session logic, or real-time commands, or TTS).  
- Store **common** logic (database, logging, config) in `core/`.  
- **Create** or re-use Avro schemas for each topic.  
- For new functionality, **add a new processor** or **agent** as needed.