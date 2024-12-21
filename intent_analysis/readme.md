# Intent Analysis

This Kafka-based application is designed to be **decoupled**, **modular**, and **extensible**:

- **Two existing processors** (transcription + intent) show the overall flow from raw text to decision to TTS.  
- **Kafka** acts as the data fabric, passing messages between these independently running consumers/producers.  
- **Agents** (like `DecisionAgent`) and **services** (like the TTS service) are each in their own modules, making them easy to replace, extend, or augment.  
- **Adding a new processor** simply means subclassing `BaseKafkaProcessor` and hooking into the topics you care about.  
- **Adding a new agent** means creating a new class in `agents/` and hooking it into whichever processor(s) you choose.

Below is a **high-level document** explaining the architecture and flow of this decoupled Kafka-based application. It covers:

1. **System Architecture and High-Level Flow**  
2. **Processor Concept** (and how they fit in)  
3. **TranscriptionProcessor** & **IntentProcessor** details  
4. **Kafka Message Format**  
5. **Steps to Add a New Processor**  
6. **Steps to Add a New Agent Integration**

Feel free to adapt and include these details in your README, Wiki, or other documentation.

---

# 1. System Architecture Overview

The system is organized into **three** primary layers:

1. **Core**:  
   - Handles basic infrastructure and utilities, such as configuration loading (`config_loader.py`), a base class for Kafka processors (`base_processor.py`), and a simplified logger (`logger.py`).

2. **Processors**:  
   - **TranscriptionProcessor**: Consumes transcriptions from a Kafka topic, runs them through a decision-making agent (LLM), and publishes the resulting “action” messages to another topic.  
   - **IntentProcessor**: Consumes the resulting “action” or “intent” messages and performs text-to-speech.  

3. **Services/Agents**:  
   - **DecisionAgent**: Interacts with a Large Language Model (LLM) (via Ollama) to decide if a user’s transcription requires an action.  
   - **TTS Service**: Connects to an external text-to-speech endpoint to generate audio.

**Message Flow** looks like this:

1. **Transcriptions** are published to `transcriptions.all`.  
2. **TranscriptionProcessor** consumes these from `transcriptions.all`, consults the **DecisionAgent**, then (if needed) publishes an “action required” message to `transcriptions.agent.action`.  
3. **IntentProcessor** consumes from `transcriptions.agent.action`, and if there is a `reasoning` field, it plays TTS audio.

Because each processor has its own Kafka consumer group and topics, they are loosely coupled. You can disable, upgrade, or replace processors independently without impacting the rest of the pipeline—**that’s the essence of the decoupled architecture**.

---

# 2. Processor Concept

A **Processor** is simply a **class** that inherits from `BaseKafkaProcessor` and overrides `process_records()` to implement custom logic.  
- **Key Responsibilities**:  
  1. **Consume** from one or more Kafka topics (by calling `init_consumer(topic_name)`).  
  2. **Process** the messages (e.g., parse JSON, call external services, do some business logic).  
  3. **Produce** (optional) new messages to other Kafka topics (by calling `init_producer()` and using `self.producer.send(...)`).  
  4. **Gracefully shutdown** on signals (SIGINT/SIGTERM).

By encapsulating the consumption/production logic into a single, coherent “processor,” you gain **reuse** of the Kafka handling (via `BaseKafkaProcessor`) and consistent logging.

---

# 3. Existing Processors

Currently, two processors ship with this framework:

1. **TranscriptionProcessor**  
   - **Input Topic**: `transcriptions.all`  
   - **Output Topic**: `transcriptions.agent.action`  
   - **Logic**:  
     1. Reads **raw transcription** strings.  
     2. Calls `DecisionAgent` to see if an action is required.  
       - If `action_required_decision` is `True`, it publishes a JSON message to `transcriptions.agent.action`.  
     3. The message posted includes fields like `original_transcription`, `refined_prompt`, `categorization`, and `reasoning`.

2. **IntentProcessor**  
   - **Input Topic**: `transcriptions.agent.action`  
   - **Logic**:  
     1. Consumes any messages that indicate an action is required (or some “reasoning” to play).  
     2. Calls the **TTS Service** on the `reasoning` field.  
     3. Plays the generated MP3 audio.

Both processors rely on the decoupled “publish/subscribe” mechanism of Kafka. If any consumer is offline, messages remain in the Kafka topic until that consumer is ready to process them (within retention policies).

---

# 4. Kafka Message Format

## 4.1 Transcription Events

When a transcription is first created, it’s published (as a **string**) to the `transcriptions.all` topic. For instance:

```
"Hello, can you turn on the living room lights?"
```

(That’s a plain UTF-8 string, or you could wrap it in JSON if preferred.)

## 4.2 DecisionAgent Output

When `TranscriptionProcessor` deems action is needed, it produces a **JSON** object to `transcriptions.agent.action`. The structure is typically:

```json
{
  "original_transcription": "Hello, can you turn on the living room lights?",
  "refined_prompt": "Please switch on the living room lights.",
  "categorization": "home_automation",
  "reasoning": "User requested to turn on living room lights."
}
```

## 4.3 Intent to TTS

**IntentProcessor** consumes JSON messages from `transcriptions.agent.action` and looks specifically for a `reasoning` field. You can tailor the code to also check for or use the `refined_prompt`, `categorization`, etc.

---

# 5. Implementing Your Own Processor

Let’s say you want a new processor called **`TopicAnalysisProcessor`** that does something else (like logging certain messages or forwarding them to a remote API). The steps are:

1. **Create a new file** in `processors/`, e.g., `topic_analysis_processor.py`.  
2. **Inherit** from `BaseKafkaProcessor`:
   ```python
   from core.base_processor import BaseKafkaProcessor
   from core.logger import info, warning, error, debug

   class TopicAnalysisProcessor(BaseKafkaProcessor):
       def __init__(self, config):
           super().__init__(config)
           kafka_config = config["kafka"]

           self.input_topic = "some_new_input_topic"  
           self.output_topic = "some_new_output_topic"  # if you need one

           self.init_consumer(self.input_topic)
           self.init_producer()  # if needed

       def process_records(self):
           info(f"Listening on topic '{self.input_topic}'...")
           for message in self.consumer:
               if not self.running:
                   break

               raw_data = message.value
               debug(f"Received message: {raw_data}")

               try:
                   # Do custom logic here
                   # If you want to produce an output:
                   self.producer.send(self.output_topic, {"processed_data": raw_data})
               except Exception as e:
                   error(f"Error: {e}")

           self.shutdown()
   ```
3. **Create a run script** in the project root (e.g., `run_topic_analysis_processor.py`) that loads config and runs your processor:
   ```python
   from core.config_loader import load_config
   from processors.topic_analysis_processor import TopicAnalysisProcessor
   from core.logger import error

   if __name__ == "__main__":
       try:
           config = load_config("config/config.yml")
           processor = TopicAnalysisProcessor(config)
           processor.run()
       except Exception as e:
           error(f"Failed to start TopicAnalysisProcessor: {e}")
   ```
4. **Add any new config keys** to your `config.yml` if needed (like new topics, new external services, etc.).  
5. **Launch** your new processor with `python run_topic_analysis_processor.py`.

Because the underlying Kafka setup and graceful shutdown logic are provided by `BaseKafkaProcessor`, you don’t have to re-implement them. This is what gives the framework a modular, “plug-and-play” feel.

---

# 6. Adding a New Agent Integration

Suppose you want to integrate a new LLM or a rules-based agent instead of `DecisionAgent`. Here’s how:

1. **Create a new agent class** in `agents/`, for example `my_custom_agent.py`.  
   ```python
   from pydantic import BaseModel, Field

   class MyAgentDecision(BaseModel):
       action_required_decision: bool = Field(...)
       reasoning: str = Field(...)
       categorization: str = Field(..., nullable=True)
       refined_prompt: str = Field(..., nullable=True)

   class MyCustomAgent:
       def __init__(self, config):
           # Load any config needed, such as endpoints, auth keys, etc.
           pass

       def evaluate_transcription(self, transcription: str) -> MyAgentDecision:
           # Your logic (could be an external LLM or a local rules-based system)
           # For demonstration, returning a dummy decision:
           return MyAgentDecision(
               action_required_decision=True,
               reasoning="Custom agent says action is required",
               categorization="custom_category",
               refined_prompt=transcription
           )
   ```
2. **Modify/Extend** the relevant processor to use the new agent. For example, if you want `TranscriptionProcessor` to use `MyCustomAgent`, just replace the existing `DecisionAgent`:
   ```python
   from agents.my_custom_agent import MyCustomAgent

   class TranscriptionProcessor(BaseKafkaProcessor):
       def __init__(self, config):
           super().__init__(config)
           ...
           self.decision_agent = MyCustomAgent(config)
   ```
3. **Adjust** your code to handle the new agent’s pydantic model if it differs in structure from `AgentDecision`. For instance, you might rename some fields or change the logic that checks `action_required_decision`.

You can also create a completely new processor that references your new agent class. The main advantage is that the **overall pipeline** remains the same; you’re only swapping the logic that determines “Does this transcription require further action?”

