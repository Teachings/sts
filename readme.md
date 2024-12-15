# Wiki: Setting Up Speech-to-Text with VAD and Faster Whisper

## Introduction
This project enables real-time speech-to-text transcription using Faster Whisper and voice activity detection (VAD). It detects when a user speaks, transcribes the speech, and continues recording without losing audio during transcription.

### Key Features
- **Real-time Voice Activity Detection**: Automatically detects speech and pauses.
- **Parallel Transcription**: Ensures transcription doesn't block recording.
- **Cross-Device Compatibility**: Supports various audio devices.

---

## Architecture Overview
The application employs a **Producer-Consumer Model**:

1. **Producer (Recording)**:
   - Captures audio chunks in real-time from the microphone.
   - Uses VAD to determine when the user is speaking.
   - Sends detected speech audio chunks to a queue.

2. **Consumer (Transcription)**:
   - Continuously processes audio chunks from the queue.
   - Transcribes speech using Faster Whisper.
   - Outputs transcription results incrementally.

### High-Level Flow
1. **Audio Input**: User selects a microphone.
2. **Voice Activity Detection**:
   - Detects speech and pauses.
   - Sends audio chunks with speech to a queue.
3. **Parallel Processing**:
   - Recording and transcription run in separate threads.
4. **Output**: Transcriptions are displayed incrementally in real-time.

---

## Setup Instructions

### Prerequisites
1. **Hardware**:
   - NVIDIA GPU with CUDA support (e.g., RTX 3090).
   - Supported microphone (e.g., Elgato Wave XLR, Jabra SPEAK 410).

2. **Software**:
   - **Operating System**: Ubuntu 20.04 or later.
   - Python 3.8+.
   - NVIDIA CUDA Toolkit and cuDNN.

### Install CUDA and cuDNN
Follow these steps to install CUDA Toolkit 12.6 and cuDNN:

#### 1. Install CUDA
```bash
wget https://developer.download.nvidia.com/compute/cuda/12.6.3/local_installers/cuda_12.6.3_560.35.05_linux.run
sudo sh cuda_12.6.3_560.35.05_linux.run
```

#### 2. Install cuDNN
```bash
wget https://developer.download.nvidia.com/compute/cudnn/9.6.0/local_installers/cudnn-local-repo-ubuntu2204-9.6.0_1.0-1_amd64.deb
sudo dpkg -i cudnn-local-repo-ubuntu2204-9.6.0_1.0-1_amd64.deb
sudo cp /var/cudnn-local-repo-ubuntu2204-9.6.0/cudnn-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cudnn
```

### Install Python Dependencies
For easier dependency management, create a `requirements.txt` file with the following content:
```text
torch
torchaudio
sounddevice
scipy
faster-whisper
termcolor
```

Then install the dependencies using:
```bash
pip install -r requirements.txt
```

### Clone the Project
```bash
git clone https://github.com/your-repository-name.git
cd your-repository-name
```

Place the `requirements.txt` file in the root of the cloned repository. To install dependencies, use:
```bash
pip install -r requirements.txt
```

### Run the Application
1. Start the application:
```bash
python speech_to_text_vad.py
```
2. Select the microphone device when prompted.
3. Speak into the microphone to see real-time transcription.

---

## Using on a Different Computer
To use this project on another system:

1. **Check GPU and CUDA Compatibility**:
   - Ensure the target system has a CUDA-enabled NVIDIA GPU.
   - Install the compatible CUDA Toolkit and cuDNN version.

2. **Clone the Repository**:
   - Clone the project to the target system.
   - Install dependencies using `pip`.

3. **Update Audio Device IDs**:
   - Use `sounddevice.query_devices()` to list available audio devices.
   - Update the script if specific devices are required.

4. **Run the Script**:
   - Execute `python speech_to_text_vad.py` and follow the prompts.

---

## Troubleshooting

### Common Issues
1. **CUDA Errors**:
   - Ensure CUDA and cuDNN are installed correctly.
   - Check if the correct `compute_type` (e.g., `float16`) is being used for the GPU.

2. **No Audio Devices Found**:
   - Verify the microphone is connected and detected by the operating system.
   - Use `sounddevice.query_devices()` to list devices.

3. **Slow Transcription**:
   - Ensure the GPU is being utilized by the Faster Whisper model.
   - Check for conflicting CPU usage.

### Debugging Tips
- Run `nvidia-smi` to verify GPU utilization.
- Use logging in the script to pinpoint errors.