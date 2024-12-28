# Intent Analysis

This Kafka-based application is designed to be **decoupled**, **modular**, and **extensible**:

- **Multiple processors** (RealTime, Persistence, Session, Aggregator, Transcription, Intent, etc.) demonstrate the flow from **raw text** to **DB** to **final TTS** or **aggregated** result.  
- **Kafka** acts as the data fabric, passing messages between these independently running consumers/producers.  
- **Agents** (like the `RealtimeAgent`, `SessionManagementAgent`, or `DecisionAgent`) and **services** (like the TTS service) are each in their own modules, making them easy to replace, extend, or augment.  
- **Adding a new processor** simply means subclassing `BaseKafkaProcessor` and hooking into the Kafka topics you care about.  
- **Adding a new agent** means creating a new class in `agents/` and hooking it into whichever processor(s) you choose.

Below is a **high-level document** explaining the architecture and flow of this decoupled Kafka-based application. It covers:

1. **System Architecture and High-Level Flow**  
2. **Processor Concept** (and how they fit in)  
3. **Key Processors** (RealTime, Session, Aggregator, Persistence, etc.)  
4. **Kafka Message Format**  
5. **Steps to Add a New Processor**  
6. **Steps to Add a New Agent**

---

## 1. System Architecture Overview

### 1.1 Three Primary Layers

1. **Core**  
   - Handles basic infrastructure and utilities, such as configuration loading (`config_loader.py`), a base class for Kafka processors (`base_processor.py`), database connectivity (`database.py`), and a simplified logger (`logger.py`).

2. **Processors**  
   - **RealTimeProcessor**: Consumes transcriptions in real time, decides if immediate action is needed, and also queries a SessionManagementAgent to create/destroy sessions.  
   - **SessionProcessor**: Listens for session creation/destruction commands, updates the DB, and triggers the aggregator when sessions end.  
   - **AggregatorProcessor**: Gathers transcriptions within a session’s timeframe, aggregates them, and stores the summary.  
   - **PersistenceProcessor**: Simply stores all raw transcriptions into a Postgres database.  
   - **IntentProcessor**: Takes “action required” messages and performs text-to-speech (or other final actions).  
   - **TranscriptionProcessor** (optional/legacy): Consumes from `transcriptions.all` and uses a simpler agent model (e.g. `DecisionAgent`) to publish an “action” message.

3. **Agents / Services**  
   - **RealtimeAgent**: Interacts with an LLM to determine if a user’s utterance requires immediate action (e.g., “turn off the lights”).  
   - **SessionManagementAgent**: Another LLM-based agent that decides whether to CREATE, DESTROY, or ignore session requests.  
   - **DecisionAgent** (an older or alternate agent): Decides if an action is required for each transcription.  
   - **TTS Service**: Connects to an external text-to-speech endpoint to generate audio from `reasoning`.

### 1.2 High-Level Message Flow

1. **Speech-to-Text** publishes transcriptions to **`transcriptions.all`**.  
2. **PersistenceProcessor** stores everything in Postgres.  
3. **RealTimeProcessor**:
   - Checks if any immediate action is needed (publishes to **`transcriptions.agent.action`** if so).  
   - Also calls **SessionManagementAgent** to see if we should create or destroy a session (publishes to **`sessions.management`** if so).  
4. **SessionProcessor**:
   - Consumes from **`sessions.management`**, updates `sessions` table (e.g., sets `active=FALSE` and `end_time` when the user says “end session”).  
   - Publishes an **aggregation request** (`aggregations.request`) if the session ends.  
5. **AggregatorProcessor**:
   - Consumes from **`aggregations.request`**, queries transcriptions within session boundaries, aggregates them, and stores the result in `sessions.summary`.  
6. **IntentProcessor** (optionally):
   - Consumes from **`transcriptions.agent.action`** and uses TTS to speak any `reasoning` or instructions.

Because each processor has its **own** Kafka consumer group and topics, they are loosely coupled: you can disable, upgrade, or replace any individual piece independently without impacting the rest.

---

## 2. Processor Concept

A **Processor** is a **class** inheriting from `BaseKafkaProcessor` that overrides `process_records()` with custom logic.  

1. **Initialize** in the constructor, calling `self.init_consumer(topic_name)` and optionally `self.init_producer()`.  
2. **Consume** messages in `process_records()` with a loop over `self.consumer`.  
3. **Perform** the required work: parse JSON, call an agent, store or retrieve data from the DB, etc.  
4. **Produce** (optional) to another topic with `self.producer.send(...)`.  
5. **Gracefully shutdown** on SIGINT/SIGTERM.

Thanks to the `BaseKafkaProcessor`, you don’t have to rewrite the Kafka consumer/producer logic every time.

---

## 3. Key Processors in This Project

### 3.1 RealTimeProcessor
- **Input**: `transcriptions.all`  
- **Logic**:
  1. Calls **RealtimeAgent** to see if an immediate action is required. If yes, publishes to `transcriptions.agent.action`.  
  2. Calls **SessionManagementAgent** to see if we should create/destroy sessions. If yes, publishes to `sessions.management`.  
- **File**: `processors/real_time_processor.py`

### 3.2 SessionProcessor
- **Input**: `sessions.management`  
- **Logic**:
  1. Creates or destroys a session in the `sessions` table.  
  2. Triggers `aggregations.request` when a session is ended, so the aggregator can finalize that conversation’s text.  
- **File**: `processors/session_processor.py`

### 3.3 AggregatorProcessor
- **Input**: `aggregations.request`  
- **Logic**:
  1. Finds all transcriptions matching the session’s start/end times.  
  2. Aggregates them (joins into one text block).  
  3. Stores the summary in `sessions.summary`.  
- **File**: `processors/aggregator_processor.py`

### 3.4 PersistenceProcessor
- **Input**: `transcriptions.all`  
- **Logic**:
  - Takes each message, extracts user/timestamp/text, and inserts into the `transcriptions` table.  
- **File**: `processors/persistence_processor.py`

### 3.5 IntentProcessor
- **Input**: `transcriptions.agent.action`  
- **Logic**:
  - Takes “action required” messages, calls TTS on the `reasoning` field, and plays the audio.  
- **File**: `processors/intent_processor.py`

### 3.6 TranscriptionProcessor (Optional / Legacy)
- **Input**: `transcriptions.all`  
- **Logic**:
  - Uses a simpler `DecisionAgent` to decide if an action is required. If yes, publishes to `transcriptions.agent.action`.  
- **File**: `processors/transcription_processor.py`

---

## 4. Kafka Message Format

### 4.1 Raw Transcription Messages

Typically, these arrive on `transcriptions.all` as JSON:

```json
{
  "timestamp": "2024-12-21 23:00:21",
  "text": "The user is seeking assistance with accessibility features.",
  "user": "mukul"
}
```

### 4.2 Action Required / Real-Time Output

If an **agent** decides action is needed, it might publish:

```json
{
  "original_text": "Turn off the lights in the living room.",
  "reasoning": "The user wants to control smart home devices.",
  "categorization": "home_automation",
  "refined_prompt": "Turn off the living room lights.",
  "user_id": "mukul",
  "timestamp": "2024-12-21 23:00:21"
}
```

### 4.3 Session Management Commands

When the **SessionManagementAgent** says `CREATE` or `DESTROY`, we publish to `sessions.management`:

```json
{
  "session_decision": "CREATE",
  "reasoning": "User said 'start a new brainstorming session.'",
  "user_id": "mukul",
  "timestamp": "2024-12-21 23:00:21"
}
```

*(Similarly for `DESTROY` or `NO_ACTION`.)*

### 4.4 Aggregator Requests

When the **SessionProcessor** finishes a session, it sends:

```json
{
  "session_id": 123,
  "user_id": "mukul"
}
```

to `aggregations.request`, prompting the **AggregatorProcessor** to compile all transcriptions in that session.

---

## 5. Steps to Add a New Processor

If you want to create a new processing microservice, say **“TopicAnalysisProcessor”**, you would:

1. **Create** a file in `processors/`, e.g. `topic_analysis_processor.py`:
   ```python
   from core.base_processor import BaseKafkaProcessor
   from core.logger import info, debug, error

   class TopicAnalysisProcessor(BaseKafkaProcessor):
       def __init__(self, config):
           super().__init__(config)
           kafka_config = config["kafka"]
           self.consumer_group_id = "topic_analysis_consumer_group"
           self.input_topic = "some_input_topic"
           self.output_topic = "some_output_topic"

           self.init_consumer(self.input_topic)
           self.init_producer()

       def process_records(self):
           info(f"Listening on topic '{self.input_topic}'...")
           for msg in self.consumer:
               if not self.running:
                   break
               raw_str = msg.value
               debug(f"Received: {raw_str}")
               try:
                   # Custom logic
                   # If you want to produce an output:
                   self.producer.send(self.output_topic, {"processed_data": raw_str})
               except Exception as e:
                   error(f"Error in TopicAnalysisProcessor: {e}")

           self.shutdown()
   ```
2. **Create** a run script (e.g. `run_topic_analysis_processor.py`):
   ```python
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
3. **Add** any needed topic references (like `"some_input_topic"` / `"some_output_topic"`) into `config/config.yml`.  
4. **Run**: `python run_topic_analysis_processor.py`.

The **base** class, `BaseKafkaProcessor`, handles signal handling, consumer/producer initialization, etc., so you **only** write the custom logic. This makes it easy to plug new functionality into the overall pipeline.

---

## 6. Adding a New Agent

If you want a **new** LLM-based agent:

1. **Create** a new file in `agents/`, for example `my_custom_agent.py`.  
2. **Define** a pydantic model for the agent’s output (like `MyAgentDecision`).  
3. **Implement** the agent class, hooking into your desired LLM or business logic.  
4. **Modify** whichever processor(s) should call this agent. For instance, if the new agent is a **“Topic Tagger”**, you might modify `RealTimeProcessor` or create a new “TopicTagProcessor.”  
5. **Adjust** the code to handle the new agent’s JSON structure, if needed.

This approach keeps each agent’s logic in a **separate** module, making it easy to switch or update LLM prompts/engines without rewriting the entire pipeline.

---

## Conclusion

**This project** now supports:

1. **Real-time** checks for immediate user commands (**RealTimeProcessor** + **RealtimeAgent**).  
2. **Session-based** creation and destruction through an **LLM agent** that decides if the user actually wants to “start/close session.”  
3. **Automated** aggregation once a session ends.  
4. **Extensibility** via easily adding new processors or agent classes.

**Best Practices**:
- Keep each processor’s responsibilities **clear** (one for DB insertion, one for session logic, one for aggregation).  
- Use **separate** Kafka consumer group IDs for each processor if they must all receive the same topic’s messages.  
- Store any **shared** logic (db connections, config, logging) in `core/`.  
- **Test** each processor individually, since they’re decoupled by Kafka topics.