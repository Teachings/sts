import sounddevice as sd
import json
from helpers import log


def load_config():
    """Load configuration from config.json."""
    try:
        with open("config.json", "r") as config_file:
            return json.load(config_file)
    except Exception as e:
        log(f"Error loading config.json: {str(e)}", level="ERROR")
        return {"favorite_microphones": []}


def list_audio_devices():
    """Lists audio devices based on favorites in config.json."""
    config = load_config()
    favorites = config.get("favorite_microphones", [])
    devices = sd.query_devices()

    if not favorites:
        # No favorites defined, return all devices
        log("No favorite microphones defined. Showing all available devices.", level="INFO")
        return {idx: dev["name"] for idx, dev in enumerate(devices)}

    # Filter devices based on partial name matches with favorites
    relevant_devices = {
        idx: dev["name"]
        for idx, dev in enumerate(devices)
        if any(fav.lower() in dev["name"].lower() for fav in favorites)
    }

    if len(relevant_devices) == 1:
        # Automatically pick the single favorite device
        log(f"Automatically selected favorite microphone: {list(relevant_devices.values())[0]}", level="SUCCESS")
        return relevant_devices

    if not relevant_devices:
        log("No favorite microphones found in the available devices. Showing all devices.", level="WARNING")
        return {idx: dev["name"] for idx, dev in enumerate(devices)}

    return relevant_devices


def get_device_sampling_rate(device_id):
    """Fetch the default sampling rate for the selected device."""
    return int(sd.query_devices(device_id)["default_samplerate"])
