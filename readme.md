# **Wiki: Setting Up Speech-to-Speech with VAD, Faster Whisper and Kafka**

## **Introduction**
This project provides real-time speech-to-text transcription using Faster Whisper and voice activity detection (VAD). It efficiently detects speech, transcribes audio, and supports seamless real-time processing with optional Kafka-based post-processing.

### **Key Features**
- **Advanced Voice Activity Detection**: Detects speech and pauses with high accuracy using the Silero VAD model.
- **Real-Time Parallel Processing**: Ensures recording and transcription run simultaneously without interruptions.
- **Post-Processing Integration**: Supports custom actions after transcription, including Kafka-based text-to-speech (TTS) integration.
- **Cross-Device Compatibility**: Works with various audio devices, including user-defined favorites.

---

## **Architecture Overview**
The application employs a **Producer-Consumer Model**:

1. **Producer (Recording)**:
   - Records audio chunks in real-time.
   - Uses VAD to detect speech segments.
   - Sends detected audio files to a processing queue.

2. **Consumer (Transcription)**:
   - Processes audio chunks from the queue.
   - Transcribes speech using Faster Whisper.
   - Outputs incremental and grouped transcription results.

3. **Kafka Integration**:
   - Transcription results can be sent to a Kafka topic.
   - A Kafka consumer listens for messages on the topic and converts text to speech using a TTS API.

### **High-Level Flow**
1. **Audio Input**: User selects or auto-detects a microphone.
2. **Voice Activity Detection**:
   - Identifies speech and pauses.
   - Saves speech segments to temporary files.
   - Sends file paths to a queue for transcription.
3. **Parallel Processing**:
   - Recording and transcription occur in separate threads.
4. **Post-Processing**:
   - Transcription results are sent to Kafka for downstream applications like TTS.

---

## **Setup Instructions**

### **Prerequisites**

#### **Hardware**
- NVIDIA GPU with CUDA support (e.g., RTX 3090 or higher recommended).
- Supported microphone (e.g., Elgato Wave XLR, Jabra SPEAK 410).

#### **Software**
- **Operating System**: Ubuntu 20.04+ or Windows 10+.
- Python 3.8+.
- NVIDIA CUDA Toolkit and cuDNN.

---

### **Installation Steps**

#### 1. **Install CUDA and cuDNN**
Follow these steps to install the latest CUDA Toolkit and cuDNN:

##### **CUDA Installation**
```bash
wget https://developer.download.nvidia.com/compute/cuda/12.6.3/local_installers/cuda_12.6.3_560.35.05_linux.run
sudo sh cuda_12.6.3_560.35.05_linux.run
```

##### **cuDNN Installation**
```bash
wget https://developer.download.nvidia.com/compute/cudnn/9.6.0/local_installers/cudnn-local-repo-ubuntu2204-9.6.0_1.0-1_amd64.deb
sudo dpkg -i cudnn-local-repo-ubuntu2204-9.6.0_1.0-1_amd64.deb
sudo cp /var/cudnn-local-repo-ubuntu2204-9.6.0/cudnn-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cudnn
```

#### 2. **Clone the Repository**
```bash
git clone https://github.com/Teachings/sts.git
cd sts
```

#### 3. **Install Python Dependencies**

Install the dependencies:
```bash
pip install -r requirements.txt
```

#### 4. **Run the Application**
1. Start the transcription application:
   ```bash
   python stt/main.py
   ```
2. Start the Kafka consumer for text-to-speech:
   ```bash
   python kafka_consumer.py
   ```
3. Select a microphone from the listed devices when prompted.
4. Speak into the microphone to see real-time transcription and hear the synthesized speech.

#### 5. **Setup Kafka**
Navigate to the `kafka` directory and use `docker-compose` to start Kafka services:
```bash
cd kafka
docker-compose up -d
```

---

## **Using on a Different System**

1. **Verify GPU and CUDA Compatibility**:
   - Ensure the system has a CUDA-enabled NVIDIA GPU.
   - Install compatible versions of CUDA Toolkit and cuDNN.

2. **Clone the Repository**:
   - Clone the project to the target system.
   - Install dependencies using `pip`.

3. **Configure Audio Devices**:
   - Use `sounddevice.query_devices()` to list available microphones.
   - Modify `config.yml` to specify preferred devices if necessary.

4. **Run the Application**:
   - Start the transcription and Kafka consumer as described above.

---

## **Troubleshooting**

### **Common Issues**
1. **CUDA Errors**:
   - Verify that CUDA and cuDNN are correctly installed.
   - Ensure the Faster Whisper model is configured to use `float16` for GPU acceleration.

2. **No Audio Devices Found**:
   - Confirm that the microphone is properly connected and recognized by the OS.
   - Run `sounddevice.query_devices()` to check available devices.

3. **Kafka Connection Issues**:
   - Ensure that the Kafka broker is running and accessible.
   - Verify that the `BROKER` and `TOPIC_NAME` in `kafka_consumer.py` match the Kafka setup.

4. **Slow Transcription**:
   - Ensure that the application is utilizing the GPU.
   - Use `nvidia-smi` to monitor GPU utilization.

### **Debugging Tips**
- Check logs for detailed error messages.
- Use `nvidia-smi` to ensure GPU resources are allocated to the application.
- Verify that the correct microphone is selected.

---

## Intent Analysis

This sub-project implements **text-to-speech** message handling, **session management**, **real-time agent** decision-making, and **aggregation** of transcriptions for final summaries. It’s built around **Kafka** for message passing, **Postgres** for storing transcriptions, and **LLM-based agents** (using **ollama**) to make decisions on how to process user requests.

### Core Ideas

1. **Transcriptions** are published to **`transcriptions.all`**.  
2. **PersistenceProcessor** stores each transcription in **Postgres**, tagged by user ID and timestamp.  
3. **RealTimeProcessor** analyzes each transcription in real time:
   - Checks if it needs an **immediate action** (turn on lights, do a web search, etc.).  
   - Determines whether to **create**, **destroy**, or **ignore** session boundaries.  
4. **SessionProcessor** listens for session commands (`CREATE`, `DESTROY`, `NO_ACTION`) on **`sessions.management`**.  
   - Maintains the **sessions** table in Postgres, including a **timeout** mechanism for long sessions.  
   - Triggers an **AggregatorProcessor** when a session is destroyed.  
5. **AggregatorProcessor** gathers all transcriptions from the final session window and compiles them into a summary stored in the sessions table.  
6. **IntentProcessor** can perform text-to-speech or other post-processing on “action required” events.

This design allows each piece to be **independently** developed, tested, and scaled.

---

## Directory Structure

```
intent_analysis/
├── run_real_time_processor.py
├── run_aggregator_processor.py
├── run_session_processor.py
├── run_persistence_processor.py
├── init_db.py
├── run_intent_processor.py
├── run_transcription_processor.py
├── services/
│   └── tts_service.py
├── core/
│   ├── database.py
│   ├── logger.py
│   ├── base_processor.py
│   └── config_loader.py
├── agents/
│   ├── realtime_agent.py
│   ├── session_management_agent.py
│   └── decision_agent.py
├── processors/
│   ├── transcription_processor.py
│   ├── aggregator_processor.py
│   ├── intent_processor.py
│   ├── persistence_processor.py
│   ├── session_processor.py
│   └── real_time_processor.py
└── config/
    ├── prompts.yml
    └── config.yml
```

### Key Subdirectories

1. **agents/**: LLM-based logic (e.g., RealTimeAgent, SessionManagementAgent, DecisionAgent).  
2. **processors/**: Kafka consumers that orchestrate reading/writing messages, calling agents, storing data, etc.  
3. **core/**: Reusable utilities (database connections, logging, base classes, config loading).  
4. **services/**: Additional micro-services or integration logic (e.g., TTS).

---

## How Each Processor Works

Below is a brief explanation of each processor’s role. Each one **inherits** from `BaseKafkaProcessor`, sets up a **KafkaConsumer** and optionally a **KafkaProducer**, and implements the `process_records()` method.

### 1. **PersistenceProcessor**
- **Topic**: Consumes from `transcriptions.all`.  
- **Purpose**: Stores each incoming transcription into the **transcriptions** table in Postgres.  
- **File**: `processors/persistence_processor.py`.

### 2. **RealTimeProcessor**
- **Topic**: Consumes from `transcriptions.all`.  
- **Purpose**:
  - Passes transcriptions to the **RealtimeAgent** to detect if immediate action is needed.
    - If yes, publishes to `transcriptions.agent.action`.  
  - Passes transcriptions to **SessionManagementAgent** to decide whether to CREATE/DESTROY/NO_ACTION for sessions.
    - If CREATE/DESTROY, publishes to `sessions.management`.  
- **File**: `processors/real_time_processor.py`.

### 3. **SessionProcessor**
- **Topic**: Consumes from `sessions.management`.  
- **Purpose**:
  - Updates the **sessions** table in Postgres:
    - **CREATE** a new session if user has no active session or if the old session timed out.
    - **DESTROY** the current session if user explicitly requests “close the session.”  
  - Once a session is destroyed, publishes an **aggregation request** to `aggregations.request`.  
- **File**: `processors/session_processor.py`.

### 4. **AggregatorProcessor**
- **Topic**: Consumes from `aggregations.request`.  
- **Purpose**:
  - Upon receiving a “session_id,” fetches all transcriptions in that session’s start/end time window from the DB.
  - Joins them into one **summary** and updates the `sessions.summary` field.  
- **File**: `processors/aggregator_processor.py`.

### 5. **TranscriptionProcessor** (Optional Legacy)
- **Topic**: Consumes from `transcriptions.all`.  
- **Purpose**: An **alternative** or **demo** processor that uses `DecisionAgent` for intent detection and publishes “action” messages.  
- **File**: `processors/transcription_processor.py`.

### 6. **IntentProcessor**
- **Topic**: Consumes from `transcriptions.agent.action`.  
- **Purpose**:
  - Reads the “reasoning” field from an agent’s action message and calls a TTS endpoint to “speak” the response.  
- **File**: `processors/intent_processor.py`.

---

## Agents

**Agents** are classes that talk to the **ollama** LLM and produce structured JSON decisions (via Pydantic).

1. **RealtimeAgent** (`agents/realtime_agent.py`)
   - Decides if an immediate real-time action is needed.  

2. **SessionManagementAgent** (`agents/session_management_agent.py`)
   - Decides if the user’s utterance should CREATE, DESTROY, or do NO_ACTION for session management.  

3. **DecisionAgent** (`agents/decision_agent.py`)
   - A generic agent that decides if an action is required (used by `TranscriptionProcessor` in the older pipeline).  

Each agent has a corresponding **system prompt** in **`config/prompts.yml`**.

---

## Configuration

All configs are in **`config/config.yml`**.  
Key sections include:

- **kafka**: Contains broker addresses, consumer groups, and topic names.  
- **db**: Postgres connection parameters.  
- **ollama**: LLM (model name, host URL, etc.).  
- **text_to_speech**: TTS endpoints, API keys, etc.  
- **app**: Additional project-wide settings like `voice_session_timeout_hours`.

---

## How To Run

1. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure Kafka + Postgres** are running (e.g., via Docker Compose or your preferred setup).

3. **Initialize Database**  
   ```bash
   python init_db.py
   ```
   - This creates the `transcriptions` and `sessions` tables if they don’t exist.

4. **Start Processors** (in separate terminals or background processes):
   ```bash
   python run_persistence_processor.py
   python run_real_time_processor.py
   python run_session_processor.py
   python run_aggregator_processor.py
   ```
   - (Optional) Start `run_intent_processor.py` if you want TTS on agent actions.
   - (Optional) Start `run_transcription_processor.py` if you’re using the older DecisionAgent approach.

5. **Publish Transcriptions** to `transcriptions.all`  
   - Typically from a **speech-to-text** system that sends messages like:
     ```json
     {
       "timestamp": "2024-12-21 23:00:21",
       "text": "The user is seeking assistance with accessibility features.",
       "user": "mukul"
     }
     ```
   - This triggers the pipeline:
     - **PersistenceProcessor** saves it to DB.  
     - **RealTimeProcessor** decides if it’s an immediate command or session action.

6. **Observe** logs in each processor for real-time debugging information (`info`, `debug`, `error` logs).

---

## Data Flow Summary

1. **Speech-to-text** publishes JSON to **`transcriptions.all`**.  
2. **PersistenceProcessor** saves every record in DB.  
3. **RealTimeProcessor**:
   - Uses **RealtimeAgent** to see if any immediate action is needed.  
     - If yes, publishes to **`transcriptions.agent.action`**.  
   - Uses **SessionManagementAgent** to see if we should `CREATE`/`DESTROY` or do `NO_ACTION` about sessions.  
     - If `CREATE` or `DESTROY`, publishes to **`sessions.management`**.  
4. **SessionProcessor**:
   - Consumes from `sessions.management`, updates the `sessions` table, and if the session is ended, publishes a message to `aggregations.request`.  
5. **AggregatorProcessor**:
   - Consumes from `aggregations.request`, fetches transcriptions from the DB within the session window, and updates `sessions.summary`.  
6. **IntentProcessor** (optional):
   - Consumes from `transcriptions.agent.action`, reads the `reasoning` field, and performs TTS playback.

---

## Extending the System

- **Add new processors** by creating a subclass of `BaseKafkaProcessor`, hooking into new or existing topics.  
- **Add new LLM agents** for specialized tasks (similar to `RealtimeAgent` or `SessionManagementAgent`).  
- **Modify DB** via migrations or `initialize_database` for additional columns/tables.  
- **Adjust** session logic or timeouts in `SessionProcessor` to suit your needs.

This modular design ensures you can **scale** or **change** parts of the pipeline without breaking the rest—Kafka topics and the DB serve as the decoupling layer.

---