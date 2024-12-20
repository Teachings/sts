## **Project Overview**

This project performs **real-time audio transcription** with advanced functionality, ensuring seamless integration and usability. Key features include:

1. **Voice Activity Detection (VAD)**: Employs the **Silero VAD** model to detect speech in real-time with minimal latency.
2. **Audio Recording**: Utilizes efficient recording techniques with double-buffering and pause detection for uninterrupted processing.
3. **Speech Transcription**: Transcribes detected speech using the **Faster Whisper** model, with real-time updates.
4. **Post-Processing**: Supports customizable post-transcription handling, including integration with external systems like Kafka.
5. **Graceful Shutdown**: Ensures clean termination of all processes on interruption (e.g., `Ctrl+C`).

---

### **Directory Structure**
```plaintext
stt/
├── __init__.py          # Marks this directory as a Python package.
├── main.py              # Entry point of the application.
├── models.py            # Defines data models for transcriptions.
├── post_processing.py   # Implements actions triggered after transcription.
├── vad.py               # Handles audio recording and voice activity detection.
├── transcriber.py       # Performs speech transcription using Faster Whisper.
├── audio_utils.py       # Manages audio devices and sampling rates.
├── helpers.py           # Provides logging, configuration, and utility functions.
```

---

### **1. main.py**

#### **Purpose**
Acts as the central coordinator of the application:
- Manages audio device selection and configuration.
- Initializes the VAD and transcription components.
- Spawns and supervises producer (audio recording) and consumer (transcription) threads.
- Ensures smooth shutdown through signal handling.

#### **Key Highlights**
- Lists available audio devices and allows selection or auto-detection of favorites.
- Configures sampling rates dynamically based on device capabilities.
- Implements threading to enable real-time recording and transcription.

---

### **2. vad.py**

#### **Purpose**
- Manages audio recording in real-time with **SoundDevice**.
- Detects speech using **Silero VAD** and dynamically alternates between two temporary files (`temp_audio_1.wav`, `temp_audio_2.wav`) to minimize recording delays.
- Communicates detected speech segments to the transcription queue.

#### **Enhancements**
- Double-buffering ensures efficient file handling without blocking the recording process.
- Configurable pause detection threshold (default: 2 seconds) for capturing complete speech segments.

---

### **3. transcriber.py**

#### **Purpose**
- Transcribes audio files using **Faster Whisper**.
- Supports grouped transcription for cohesive and context-aware results.
- Provides real-time updates for both current and cumulative transcriptions.

#### **New Features**
- Groups transcriptions based on configurable time gaps (default: 60 seconds).
- Integrates customizable post-processing pipelines, enabling seamless integration with downstream systems.

---

### **4. post_processing.py**

#### **Purpose**
- Executes user-defined actions after each transcription.
- Current implementation includes logging and sending messages to Kafka for further processing.

#### **Key Highlights**
- Configurable Kafka integration with `broker` and `topic` settings loaded from `config.json`.
- Error-handling mechanisms for robust message delivery.

---

### **5. audio_utils.py**

#### **Purpose**
- Provides utilities for audio device management, including:
  - Filtering devices based on user preferences.
  - Fetching device-specific sampling rates for optimal VAD performance.

#### **Key Highlights**
- Automatically selects favorite microphones when defined.
- Ensures compatibility by dynamically adjusting sampling rates.

---

### **6. helpers.py**

#### **Purpose**
- Provides utility functions for structured logging, configuration management, and output formatting.
- Supports error-tolerant configuration loading and structured transcription saving.

#### **Enhancements**
- Logs transcription history to timestamped JSON files in a dedicated folder.
- Displays aggregated transcriptions grouped by timestamps for clarity.

---

### **How It All Works Together**

1. **Startup (`main.py`)**:
   - Initializes the application and sets up audio device, VAD, and transcription threads.

2. **Recording (`vad.py`)**:
   - Continuously records audio, detects voice activity, and saves segments for transcription.

3. **Transcription (`transcriber.py`)**:
   - Processes audio files, generates transcription text, and groups results contextually.

4. **Post-Processing (`post_processing.py`)**:
   - Handles user-defined actions, such as integrating with external systems.

5. **Utilities (`audio_utils.py` and `helpers.py`)**:
   - Manage audio devices, logging, and structured data storage.

6. **Shutdown**:
   - Safely terminates threads, clears queues, and cleans up temporary files.
