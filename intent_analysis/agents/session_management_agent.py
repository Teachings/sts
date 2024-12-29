import yaml
from pydantic import BaseModel, Field
from typing import Optional
from ollama import Client

class SessionManagementDecision(BaseModel):
    destroy_decision: bool = Field(
        description="Boolean indicating whether the session should be destroyed (True) or not (False)"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation for why this session destruction decision was chosen."
    )

class SessionManagementAgent:
    """
    An LLM-based agent that decides whether to DESTROY a session based on user text.
    """
    def __init__(self, config):
        ollama_config = config["ollama"]
        self.url = ollama_config["url"]
        self.model = ollama_config["model"]

        # Load session-specific system prompt
        with open(ollama_config["system_prompt_file"], 'r') as file:
            yml_prompts = yaml.safe_load(file)
            self.system_prompt = yml_prompts.get("session_management_agent_system_prompt", "") # We'll need to update this prompt

        self.client = Client(host=self.url)

    def evaluate_session_decision(self, user_text: str) -> SessionManagementDecision:
        """
        Evaluates whether to destroy an existing session based on user_text.

        Args:
            user_text: The last utterance or user request.

        Returns:
            SessionManagementDecision: An object containing the decision (destroy or not) and reasoning.
        """

        messages = [
            {"role": "system", "content": self.system_prompt.strip()},
            {"role": "user", "content": user_text}
        ]

        response = self.client.chat(
            messages=messages,
            model=self.model,
            format=SessionManagementDecision.model_json_schema()
        )
        return SessionManagementDecision.model_validate_json(response.message.content)