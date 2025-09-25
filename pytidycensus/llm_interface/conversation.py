"""Conversation management for Census Assistant.

Handles conversation state, context, and flow management.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Tracks the current state of a census data conversation."""

    # Research context
    research_question: Optional[str] = None
    topic: Optional[str] = None

    # Data parameters
    variables: List[str] = None
    variable_descriptions: Dict[str, str] = None
    geography: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    year: Optional[int] = None
    dataset: Optional[str] = None  # "acs5", "acs1", "decennial"

    # Options
    geometry: bool = False
    output_format: str = "tidy"

    # Conversation flow
    stage: str = "initial"  # initial, clarifying, variables, geography, ready, executed
    missing_info: List[str] = None

    # Results
    data_shape: Optional[str] = None
    generated_code: Optional[str] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = []
        if self.variable_descriptions is None:
            self.variable_descriptions = {}
        if self.missing_info is None:
            self.missing_info = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def is_ready_for_execution(self) -> bool:
        """Check if we have enough information to execute a census query."""
        required = ["variables", "geography"]

        # Check basic requirements
        if not all(getattr(self, field) for field in required):
            return False

        # Check that we have at least one variable
        if not self.variables:
            return False

        # Geography-specific requirements
        if self.geography in ["county", "tract", "block group", "block"] and not self.state:
            return False

        return True

    def get_missing_info(self) -> List[str]:
        """Get list of missing required information."""
        missing = []

        if not self.variables:
            missing.append("variables")

        if not self.geography:
            missing.append("geography")

        if self.geography in ["county", "tract", "block group", "block"] and not self.state:
            missing.append("state")

        if not self.year:
            missing.append("year")

        return missing


class ConversationManager:
    """Manages conversation state and flow for Census Assistant."""

    def __init__(self):
        self.state = ConversationState()
        self.message_history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.message_history.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

    def get_context_messages(self, include_system: bool = True) -> List[Dict[str, str]]:
        """Get conversation messages formatted for LLM."""
        messages = []

        if include_system:
            messages.append({"role": "system", "content": self._get_system_prompt()})

        # Add conversation history (excluding timestamps for LLM)
        for msg in self.message_history[-10:]:  # Keep last 10 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})

        return messages

    def update_state(self, updates: Dict[str, Any]):
        """Update conversation state with new information."""
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
            else:
                logger.warning(f"Unknown state key: {key}")

    def _get_system_prompt(self) -> str:
        """Generate system prompt with current state context."""
        prompt = """You are a helpful Census data assistant. Your job is to help users find and retrieve US Census data using pytidycensus.

Your capabilities:
- Help users identify the right Census variables for their research
- Suggest appropriate geographic levels
- Guide users through data collection decisions
- Generate working pytidycensus code
- Explain Census concepts and data structure

Current conversation state:
"""

        # Add current state context
        state_summary = []
        if self.state.research_question:
            state_summary.append(f"Research question: {self.state.research_question}")
        if self.state.variables:
            state_summary.append(f"Variables identified: {', '.join(self.state.variables)}")
        if self.state.geography:
            state_summary.append(f"Geography: {self.state.geography}")
        if self.state.state:
            state_summary.append(f"State: {self.state.state}")
        if self.state.year:
            state_summary.append(f"Year: {self.state.year}")

        if state_summary:
            prompt += "\n".join(state_summary)
        else:
            prompt += "No information collected yet - help the user get started."

        prompt += """

Guidelines:
- Ask clarifying questions to understand their research needs
- Suggest specific Census variables with codes when possible
- Explain geographic level tradeoffs (detail vs. coverage)
- Be helpful but concise
- When ready, generate working pytidycensus code
- Always explain what the data represents

Remember: Census data can be complex. Help users understand what they're getting."""

        return prompt

    def reset(self):
        """Reset conversation state."""
        self.state = ConversationState()
        self.message_history = []

    def export_state(self) -> str:
        """Export conversation state as JSON."""
        export_data = {"state": self.state.to_dict(), "message_history": self.message_history}
        return json.dumps(export_data, indent=2)

    def import_state(self, json_data: str):
        """Import conversation state from JSON."""
        try:
            data = json.loads(json_data)

            # Restore state
            state_dict = data.get("state", {})
            for key, value in state_dict.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)

            # Restore message history
            self.message_history = data.get("message_history", [])

        except Exception as e:
            logger.error(f"Failed to import state: {e}")
            raise
