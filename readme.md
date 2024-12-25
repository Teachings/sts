# **Wiki: Setting Up Speech-to-Text with VAD and Faster Whisper**

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

## **Key Updates**
- Added a `kafka` folder with:
  - **`docker-compose.yaml`**: Automates Kafka setup using Docker.
  - **`kafka_consumer.py`**: Consumes transcription messages and converts them to speech using a TTS API.
- Enhanced integration for post-processing with Kafka.
- Refactored to support `python stt/main.py` for application startup.
- Grouped transcriptions for better readability.