import yaml
from pydantic import BaseModel, Field
from ollama import Client
from core.logger import info, error

class AggregationResult(BaseModel):
    organized_text: str = Field(description="Meaningfully organized text with bullet points and sections.")
    summary: str = Field(description="Concise summary of the organized text.")

class AggregatorAgent:
    """
    An LLM-based agent that aggregates and summarizes text.
    """
    def __init__(self, config):
        ollama_config = config["ollama"]
        self.url = ollama_config["url"]
        self.model = ollama_config["model"]

        # Load aggregator-specific system prompt
        with open(ollama_config["system_prompt_file"], 'r') as file:
            yml_prompts = yaml.safe_load(file)
            self.system_prompt = yml_prompts.get("aggregator_agent_system_prompt", "")

        self.client = Client(host=self.url)

    def analyze_and_aggregate_text(self, aggregated_text: str) -> AggregationResult:
        """
        Analyzes the aggregated text and returns an organized version and a summary.

        Args:
            aggregated_text: The raw aggregated text from the session.

        Returns:
            AggregationResult: An object containing the organized text and its summary.
        """

        messages = [
            {"role": "system", "content": self.system_prompt.strip()},
            {"role": "user", "content": aggregated_text}
        ]
        try:
            response = self.client.chat(
                messages=messages,
                model=self.model,
                format="json"
            )
            return AggregationResult.model_validate_json(response.message.content)
        except Exception as e:
            error(f"Error during text analysis and aggregation: {e}")
            return AggregationResult(organized_text="Error during processing.", summary="Error during processing.")