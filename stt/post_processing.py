import json
from helpers import log, produce_message

def invoke_after_transcription(json_output):
    """
    This function will be called after each transcription.
    You can define the actual implementation here.
    For now, let's just log the output.
    """
    log("Post-processing transcription", level="INFO")
    # log(f"{json.dumps(json_output, indent=4)}", level="INFO")
    # Assuming data is already validated and correct
    last_transcription = json_output['transcriptions'][-1]
    # print(f"Last transcription timestamp: {last_transcription['timestamp']}")
    log(f"Producing message: {last_transcription['text']}", level="INFO", color="cyan")
    produce_message(last_transcription['text'])


