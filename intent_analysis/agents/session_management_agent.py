# agents/session_management_agent.py

import yaml
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from ollama import Client

class SessionDecision(str, Enum):
    CREATE = "CREATE"
    DESTROY = "DESTROY"
    NO_ACTION = "NO_ACTION"

class SessionManagementDecision(BaseModel):
    session_decision: SessionDecision = Field(
        description="Decision about session: CREATE, DESTROY, or NO_ACTION."
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation for why this session action (or no action) was chosen."
    )

class SessionManagementAgent:
    """
    A separate LLM-based agent that decides whether to CREATE, DESTROY,
    or take NO_ACTION regarding a session, based on user text.
    """
    def __init__(self, config):
        ollama_config = config["ollama"]
        self.url = ollama_config["url"]
        self.model = ollama_config["model"]
        
        # Load session-specific system prompt
        with open(ollama_config["system_prompt_file"], 'r') as file:
            yml_prompts = yaml.safe_load(file)
            self.system_prompt = yml_prompts.get("session_management_agent_system_prompt", "")

        self.client = Client(host=self.url)

    def evaluate_session_decision(self, user_text: str, has_active_session: bool) -> SessionManagementDecision:
        """
        user_text: The last utterance or user request.
        has_active_session: Whether we already have an active session for this user.
        """

        # We'll pass that context to the LLM as well, so the agent can decide if it wants to create/destroy/no_action.
        # For example, if has_active_session=True, the system prompt might encourage the agent to pick NO_ACTION if user isn't explicitly stopping.
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
