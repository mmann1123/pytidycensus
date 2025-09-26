"""Conversation management for Census Assistant.

Handles conversation state, context, and flow management.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _load_documentation() -> str:
    """Load pytidycensus documentation content for system prompt."""
    try:
        # Get path to documentation relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Try multiple possible paths
        possible_paths = [
            os.path.join(current_dir, "..", "..", "docs", "pytidycensus_intro.md"),
            os.path.join(current_dir, "..", "..", "..", "docs", "pytidycensus_intro.md"),
            "docs/pytidycensus_intro.md",  # Relative to working directory
        ]

        docs_path = None
        for path in possible_paths:
            if os.path.exists(path):
                docs_path = path
                break

        if docs_path and os.path.exists(docs_path):
            with open(docs_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract key sections for the system prompt
            # Remove markdown metadata and focus on functional content
            lines = content.split("\n")
            filtered_lines = []
            skip_code_cell = False
            inside_front_matter = False

            for line in lines:
                # Handle YAML front matter
                if line.strip() == "---":
                    inside_front_matter = not inside_front_matter
                    continue

                if inside_front_matter:
                    continue

                # Skip code cell markers
                if line.startswith("{code-cell}") or line.startswith(":tags:"):
                    skip_code_cell = True
                    continue
                if skip_code_cell and (line.startswith("```") or line.strip() == ""):
                    skip_code_cell = False
                    continue

                if not skip_code_cell and not line.startswith(":"):
                    filtered_lines.append(line)

            # Return a condensed version focusing on key functionality
            doc_summary = "\n".join(filtered_lines[:150])  # First 150 lines for key info
            return f"PYTIDYCENSUS DOCUMENTATION EXCERPT:\n\n{doc_summary}"

    except Exception as e:
        logger.warning(f"Could not load documentation: {e}")
        return ""

    return ""


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
    output_format: str = "wide"

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
        # Load documentation content
        doc_content = _load_documentation()

        prompt = f"""You are a helpful Census data assistant specialized in pytidycensus, a Python library for accessing US Census Bureau APIs.

IMPORTANT: You MUST only recommend pytidycensus functions. DO NOT suggest other Python Census libraries like 'census', 'cenpy', or any other packages. Always use pytidycensus.

{doc_content}

## Your Core Expertise

### Core Functions
You help users with these pytidycensus functions:
- `get_acs()`: American Community Survey data (5-year, 1-year)
- `get_decennial()`: Decennial Census data (2000, 2010, 2020)
- `get_estimates()`: Population Estimates Program
- `search_variables(pattern, year, dataset, survey)`: Find variable codes by search pattern
- `load_variables()`: Load all variables for a dataset
- `set_census_api_key()`: Set API key for data access

### Common Variables (suggest these when relevant)
**Population**: B01003_001E (total population), B01001_001E (total population by age/sex)
**Income**: B19013_001E (median household income), B19301_001E (per capita income)
**Poverty**: B17001_002E (below poverty line), B17001_001E (total for poverty status)
**Housing**: B25001_001E (housing units), B25003_002E (owner occupied), B25003_003E (renter occupied), B25077_001E (median home value), B25064_001E (median rent)
**Education**: B15003_022E (bachelor's degree), B15003_025E (graduate degree)
**Race/Ethnicity**: B02001_002E (White alone), B02001_003E (Black alone), B03003_003E (Hispanic)
**Employment**: B23025_002E (labor force), B23025_005E (unemployed)

### Geographic Requirements
- **state, county, place, tract, block group** require `state` parameter
- **tract, block group, block** require both `state` and `county` parameters
- Use state names ("Wisconsin"), postal codes ("WI"), or FIPS codes ("55")
- **DC works as**: "DC", "11", or "District of Columbia"
- 1-year ACS only available for areas with 65,000+ population

### Key pytidycensus Features
- Returns pandas DataFrames by default
- Use `geometry=True` to get GeoPandas GeoDataFrames with boundaries for mapping and spatial analysis
- Use `output="wide"` to spread variables across columns
- Use dictionary for `variables` parameter to rename: {{"income": "B19013_001E"}}
- Use `show_call=True` for debugging API calls
- Use `cache=True` for faster variable loading

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
2. **CRITICAL: Always include normalization variables if relevant** - never suggest count variables without their totals
   - For household data: include total households (B19001_001E, B11001_001E)
   - For population subgroups: include total population (B01003_001E, B02001_001E)
   - For education: include total population 25+ (B15003_001E)
   - For employment: include total labor force (B23025_002E) or working age population (B23025_001E)
   - For housing: include total housing units (B25001_001E) or occupied units (B25002_002E)
3. **CRITICAL: ALWAYS set geometry=True for spatial/mapping requests** - this automatically includes shapefiles
   - Keywords that REQUIRE geometry=True: map, mapping, spatial, geographic boundaries, visualization, plot, choropleth, GIS, spatial analysis, geographic patterns, explore, visualize
   - pytidycensus automatically handles shapefile merging - no external spatial data needed
   - Always use `data.explore()` or `data.plot()` for mapping GeoPandas DataFrames
4. Ask clarifying questions to understand research needs
5. Suggest specific variable codes with their normalization variables
6. Show calculation examples for rates/percentages (e.g., poverty_rate = below_poverty / total_for_poverty)
7. Explain geographic level tradeoffs (detail vs. sample size)
8. Recommend ACS 5-year for small geographies, 1-year for timeliness
9. Generate complete pytidycensus code with proper imports and calculations
10. Explain what the data represents and any limitations

## Code Examples With Proper Normalization
```python
import pytidycensus as tc

# Income analysis with normalization
data = tc.get_acs(
    geography="state",
    variables=[
        "B19001_002E",  # Households <$25k
        "B19001_001E",  # Total households (denominator)
    ],
    year=2022,
    output="wide",
    api_key="your_key"
)
# Calculate rate: data['low_income_rate'] = data['B19001_002E'] / data['B19001_001E']

# Education analysis with normalization
data = tc.get_acs(
    geography="county",
    variables=[
        "B15003_022E",  # Bachelor's degree
        "B15003_001E",  # Total population 25+ (denominator)
    ],
    state="CA",
    year=2022,
    output="wide",
    api_key="your_key"
)
# Calculate rate: data['college_rate'] = data['B15003_022E'] / data['B15003_001E']

# Poverty analysis with normalization
data = tc.get_acs(
    geography="tract",
    variables=[
        "B17001_002E",  # Below poverty
        "B17001_001E",  # Total for poverty status (denominator)
    ],
    state="NY",
    county="New York",
    year=2022,
    output="wide",
    api_key="your_key"
)
# Calculate rate: data['poverty_rate'] = data['B17001_002E'] / data['B17001_001E']

# SPATIAL ANALYSIS - ALWAYS use geometry=True for mapping
data = tc.get_acs(
    geography="county",
    variables=[
        "B19013_001E",  # Median income
        "B17001_002E",  # Below poverty
        "B17001_001E",  # Total for poverty (denominator)
    ],
    state="TX",
    year=2022,
    output="wide",
    geometry=True,  # CRITICAL: This includes shapefiles automatically
    api_key="your_key"
)
# Calculate poverty rate
data['poverty_rate'] = data['B17001_002E'] / data['B17001_001E']
# Create map - no external shapefiles needed!
data.explore(column='poverty_rate', legend=True, cmap='OrRd')
```

**SPATIAL KEYWORDS**: If user mentions ANY of these words, ALWAYS set geometry=True:
- map, mapping, spatial, boundaries, visualization, plot, choropleth, GIS, explore, visualize, geographic patterns, spatial analysis

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
