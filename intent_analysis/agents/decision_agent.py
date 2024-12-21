import yaml
from pydantic import BaseModel, Field
from ollama import Client

# Pydantic model for the agent's decision
class AgentDecision(BaseModel):
    action_required_decision: bool = Field(description="True if action is required, False otherwise.")
    reasoning: str = Field(description="Explanation of the decision.")
    categorization: str = Field(description="Categorization of the query.", nullable=True)
    refined_prompt: str = Field(description="Refined version of the query.", nullable=True)

class DecisionAgent:
    """
    DecisionAgent interacts with the Ollama LLM to decide
    if an action is required for a given transcription.
    """
    def __init__(self, config):
        ollama_config = config["ollama"]
        self.url = ollama_config["url"]
        self.model = ollama_config["model"]

        # Load system prompt from a YAML file
        with open(ollama_config["system_prompt_file"], 'r') as file:
            yml_prompts = yaml.safe_load(file)
            self.system_prompt = yml_prompts.get("intent_agent_system_prompt", "")

        # Initialize Ollama client
        self.client = Client(host=self.url)

    def evaluate_transcription(self, transcription: str) -> AgentDecision:
        messages = [
            {"role": "system", "content": self.system_prompt.strip()},
            {"role": "user", "content": transcription},
        ]

        response = self.client.chat(
            messages=messages,
            model=self.model,
            format=AgentDecision.model_json_schema()
        )

        return AgentDecision.model_validate_json(response.message.content)
