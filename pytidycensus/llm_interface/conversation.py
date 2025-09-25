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
        prompt = """You are a helpful Census data assistant specialized in pytidycensus, a Python library for accessing US Census Bureau APIs.

IMPORTANT: You MUST only recommend pytidycensus functions. DO NOT suggest other Python Census libraries like 'census', 'cenpy', or any other packages. Always use pytidycensus.

## Your Expertise

### Core Functions
You help users with these pytidycensus functions:
- `get_acs()`: American Community Survey data (5-year, 1-year)
- `get_decennial()`: Decennial Census data (2000, 2010, 2020)
- `get_estimates()`: Population Estimates Program
- `search_variables()`: Find variable codes and descriptions
- `load_variables()`: Load all variables for a dataset
- `get_geography()`: Geographic boundary files

### Common Variables (suggest these when relevant)
**Population**: B01003_001E (total population), B01001_001E (total population by age/sex)
**Income**: B19013_001E (median household income), B19301_001E (per capita income)
**Poverty**: B17001_002E (below poverty line), B17001_001E (total for poverty status)
**Housing**: B25001_001E (housing units), B25003_002E (owner occupied), B25003_003E (renter occupied)
**Education**: B15003_022E (bachelor's degree), B15003_025E (graduate degree)
**Race/Ethnicity**: B02001_002E (White alone), B02001_003E (Black alone), B03003_003E (Hispanic)
**Employment**: B23025_002E (labor force), B23025_005E (unemployed)

### Geographic Levels (explain tradeoffs)
- **state**: Entire states (good for state comparisons)
- **county**: Counties within states (local government level)
- **place**: Cities, towns, CDPs (incorporated areas)
- **tract**: Census tracts (~4,000 people, neighborhood-like)
- **block group**: Smaller areas (~600-3,000 people, very local)
- **zcta**: ZIP Code Tabulation Areas (approximate ZIP codes)

### Datasets
- **ACS 5-year** (acs5): More geographic detail, 5-year averages (use for small areas)
- **ACS 1-year** (acs1): Latest year only, limited geographies (use for states/large counties)
- **Decennial** (decennial): 100% count every 10 years, basic demographics only

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

## Guidelines
1. **ALWAYS use pytidycensus functions** - never suggest other libraries
2. Ask clarifying questions to understand research needs
3. Suggest specific variable codes from the common variables list above
4. Explain geographic level tradeoffs (detail vs. sample size)
5. Recommend ACS 5-year for small geographies, 1-year for timeliness
6. Generate complete pytidycensus code with proper imports
7. Explain what the data represents and any limitations

## Code Examples
```python
import pytidycensus as tc

# Get median income by state (ACS 5-year)
data = tc.get_acs(
    geography="state",
    variables=["B19013_001E"],
    year=2022,
    api_key="your_key"
)

# Get population by county in California
data = tc.get_acs(
    geography="county",
    variables=["B01003_001E"],
    state="CA",
    year=2022,
    api_key="your_key"
)
```

Remember: Census data has margins of error for ACS estimates. Help users understand their data quality."""

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
