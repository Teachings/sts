import json
import yaml
import signal
import sys
from kafka import KafkaConsumer, KafkaProducer
from pydantic import BaseModel, Field
from termcolor import colored
from ollama import Client

# Kafka configurations
BROKER = "localhost:9092"
INPUT_TOPIC = "transcriptions.all"
OUTPUT_TOPIC = "transcriptions.agent.action"
GROUP_ID = "transcription_agent_group"

# Ollama LLM Configuration
OLLAMA_API_URL = "http://localhost:11434"
client = Client(host=OLLAMA_API_URL)

# Categorization labels
task_categorizations = [
    "math_query",
    "web_search",
    "brainstorm_ideas",
    "home_automation",
    "programming_help",
    "general_help",
]

# Pydantic model for agent decision
class AgentDecision(BaseModel):
    action_required_decision: bool = Field(description="True if action is required, False otherwise.")
    reasoning: str = Field(description="Explanation of the decision.")
    categorization: str = Field(description="Categorization of the query.", nullable=True)
    refined_prompt: str = Field(description="Refined version of the query for downstream systems.", nullable=True)

# Decision Agent class
class DecisionAgent:
    def __init__(self):
        with open('prompts.yml', 'r') as file:
            self.system_prompt = yaml.safe_load(file)['intent_agent_system_prompt']

    def evaluate_transcription(self, transcription: str) -> AgentDecision:
        """Interact with Ollama server to decide if action is required."""
        ollama_prompt = f"{self.system_prompt}{transcription}"

        response = client.chat(
            messages=[
                {"role": "system", "content": self.system_prompt.strip()},
                {"role": "user", "content": transcription},
            ],
            model="qwen2.5-coder:32b",
            format=AgentDecision.model_json_schema()
        )

        return AgentDecision.model_validate_json(response.message.content)

# Kafka processor
class KafkaTranscriptionProcessor:
    def __init__(self):
        self.consumer = KafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=BROKER,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=GROUP_ID,
            value_deserializer=lambda x: x.decode("utf-8"),
        )
        self.producer = KafkaProducer(
            bootstrap_servers=BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        self.agent = DecisionAgent()
        self.running = True
        self.is_shutting_down = False  # Flag to prevent duplicate shutdown

    def process_messages(self):
        print(colored(f"Listening to topic '{INPUT_TOPIC}'...", "yellow"))
        try:
            for message in self.consumer:
                if not self.running:
                    break

                transcription = message.value
                print(colored(f"Received transcription: {transcription}", "blue"))

                try:
                    decision = self.agent.evaluate_transcription(transcription)
                    print(colored(f"Decision: {decision.model_dump_json(indent=2)}", "green"))

                    if decision.action_required_decision:
                        action_message = {
                            "original_transcription": transcription,
                            "refined_prompt": decision.refined_prompt,
                            "categorization": decision.categorization,
                            "reasoning": decision.reasoning,
                        }
                        self.producer.send(OUTPUT_TOPIC, action_message)
                        print(colored(f"Published to '{OUTPUT_TOPIC}': {action_message}", "cyan"))

                except Exception as e:
                    print(colored(f"Error processing transcription: {e}", "red"))
        finally:
            self.shutdown()

    def shutdown(self):
        """Gracefully close Kafka connections."""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            print(colored("Shutting down gracefully...", "yellow"))
            self.running = False
            self.consumer.close()
            self.producer.close()

# Signal handler
def handle_signal(signal_number, frame):
    print(colored(f"Received signal {signal_number}. Exiting...", "red"))
    processor.shutdown()
    sys.exit(0)

if __name__ == "__main__":
    processor = KafkaTranscriptionProcessor()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        processor.process_messages()
    except Exception as e:
        print(colored(f"Unexpected error: {e}", "red"))
        processor.shutdown()
        sys.exit(1)
