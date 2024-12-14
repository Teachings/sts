import sounddevice as sd
from helpers import log


def list_audio_devices():
    """Lists audio devices, only showing specific relevant devices."""
    devices = sd.query_devices()
    relevant_devices = {
        idx: dev['name']
        for idx, dev in enumerate(devices)
        if "Elgato Wave XLR" in dev['name'] or "Jabra SPEAK 410 USB" in dev['name']
    }
    if not relevant_devices:
        log("No relevant audio devices found. Exiting.", level="ERROR")
    return relevant_devices


def get_device_sampling_rate(device_id):
    """Fetch the default sampling rate for the selected device."""
    return int(sd.query_devices(device_id)['default_samplerate'])
