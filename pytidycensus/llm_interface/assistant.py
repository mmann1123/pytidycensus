"""Main Census Assistant implementation.

Provides conversational interface to Census data using LLMs.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import pytidycensus as tc

from ..variables import search_variables
from .conversation import ConversationManager, ConversationState
from .knowledge_base import (
    get_geography_guidance,
    get_normalization_variables_for_codes,
    get_variables_for_topic,
)
from .providers import LLMManager, create_default_llm_manager

logger = logging.getLogger(__name__)


class CensusAssistant:
    """LLM-driven assistant for Census data discovery and retrieval."""

    def __init__(
        self,
        census_api_key: Optional[str] = None,
        llm_manager: Optional[LLMManager] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize Census Assistant.

        Args:
            census_api_key: Census API key for data retrieval
            llm_manager: Custom LLM manager (optional)
            openai_api_key: OpenAI API key for LLM access (optional)
        """
        self.census_api_key = census_api_key
        self.llm_manager = llm_manager or create_default_llm_manager(openai_api_key)
        self.conversation = ConversationManager()

        # Cache for variable lookups
        self._variable_cache = {}

    async def chat(self, user_message: str) -> str:
        """Process user message and return assistant response."""
        try:
            # Add user message to conversation
            self.conversation.add_message("user", user_message)

            # Analyze user intent and extract information
            intent_analysis = await self._analyze_intent(user_message)

            # Update conversation state based on analysis
            if intent_analysis.get("state_updates"):
                self.conversation.update_state(intent_analysis["state_updates"])

            # Generate appropriate response
            response = await self._generate_response(intent_analysis)

            # Add assistant response to conversation
            self.conversation.add_message("assistant", response)

            return response

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I encountered an error: {str(e)}. Please try rephrasing your question."

    async def _analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """Analyze user message to understand intent and extract information."""
        analysis_prompt = f"""
Analyze this user message about Census data: "{user_message}"

Current conversation state: {json.dumps(self.conversation.state.to_dict(), indent=2)}

Extract any of the following information:
- Research topic/question
- Specific variables needed (income, population, housing, etc.)
- Geographic level (state, county, tract, etc.)
- Location (state names, city names, etc.)
- Time period (year, date range)
- Data preferences (format, visualization needs)

Also classify the intent:
- "initial": User starting new research
- "clarifying": Asking questions or providing clarifications
- "variables": Focusing on what variables to get
- "geography": Discussing geographic scope
- "ready": Ready to execute data collection
- "execute": Explicitly asking to run the query

Respond with JSON matching this structure:
{{
    "intent": "intent_category",
    "confidence": 0.8,
    "extracted_info": {{
        "research_topic": "description of research",
        "variables_mentioned": ["list", "of", "variable", "concepts"],
        "geography_mentioned": "geographic level",
        "location_mentioned": "location name",
        "year_mentioned": 2020
    }},
    "state_updates": {{
        "research_question": "refined research question",
        "topic": "topic category",
        "geography": "census geography level",
        "state": "state code or name",
        "year": 2020
    }},
    "suggested_next_steps": ["list", "of", "next", "steps"]
}}
"""

        try:
            return await self.llm_manager.structured_output(
                analysis_prompt,
                {
                    "intent": "string",
                    "confidence": "number",
                    "extracted_info": "object",
                    "state_updates": "object",
                    "suggested_next_steps": "array",
                },
            )
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {
                "intent": "clarifying",
                "confidence": 0.5,
                "extracted_info": {},
                "state_updates": {},
                "suggested_next_steps": ["Please clarify your research needs"],
            }

    async def _generate_response(self, intent_analysis: Dict[str, Any]) -> str:
        """Generate appropriate response based on intent analysis."""
        intent = intent_analysis.get("intent", "clarifying")

        # Check if we can execute a query
        if self.conversation.state.is_ready_for_execution() and intent in ["ready", "execute"]:
            return await self._execute_census_query()

        # Generate contextual response based on current state
        if intent == "initial":
            return await self._handle_initial_query(intent_analysis)
        elif intent == "variables":
            return await self._handle_variable_discussion(intent_analysis)
        elif intent == "geography":
            return await self._handle_geography_discussion(intent_analysis)
        else:
            return await self._handle_general_discussion(intent_analysis)

    async def _handle_initial_query(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle initial research query."""
        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
This user is starting a new Census data research project. Based on the analysis:
{json.dumps(intent_analysis, indent=2)}

Please:
1. Acknowledge their research interest
2. Ask 2-3 focused questions to help them get the right data
3. Be encouraging and helpful

Focus on understanding:
- What specific topic they're researching
- What geographic area they care about
- What time period they need
- What they want to do with the data
""",
            }
        )

        return await self.llm_manager.chat_completion(messages)

    async def _handle_variable_discussion(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle discussion about Census variables."""
        variables_mentioned = intent_analysis.get("extracted_info", {}).get(
            "variables_mentioned", []
        )

        if variables_mentioned:
            # Search for relevant Census variables (includes selective normalization)
            variable_suggestions = await self._search_census_variables(variables_mentioned)

            messages = self.conversation.get_context_messages()
            messages.append(
                {
                    "role": "user",
                    "content": f"""
The user is discussing Census variables. I found these relevant variables:
{json.dumps(variable_suggestions, indent=2)}

Please:
1. Suggest the most appropriate variables for their research
2. For variables marked as (DENOMINATOR), explain these are needed for calculating rates/percentages
3. Explain what each variable represents
4. Show calculation examples for any rate variables (e.g., percentage = count/total * 100)
5. Ask if they need additional related variables
6. Move toward discussing geographic level if variables look good

NOTE: The system now automatically includes normalization variables only when needed - variables containing 'median', 'mean', 'rate', etc. don't need denominators.
""",
                }
            )

            return await self.llm_manager.chat_completion(messages)

        else:
            # General variable discussion
            messages = self.conversation.get_context_messages()
            return await self.llm_manager.chat_completion(messages)

    async def _handle_geography_discussion(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle discussion about geographic levels."""
        # Get geography guidance from knowledge base
        current_geo = self.conversation.state.geography
        geo_info = get_geography_guidance(current_geo) if current_geo else {}

        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
The user is discussing geography. Current state shows:
- Geography: {self.conversation.state.geography}
- State: {self.conversation.state.state}
- Research topic: {self.conversation.state.research_question}

Knowledge base info for current geography ({current_geo}):
{json.dumps(geo_info, indent=2) if geo_info else "No specific info available"}

Please help them choose the right geographic level by:
1. Using the knowledge base info to explain tradeoffs (detail vs sample size)
2. Suggesting what makes sense for their research needs
3. If they need state/county specification, ask for it specifically
4. Explain any limitations or requirements for their chosen geography
5. Move toward execution if everything looks ready

Remember to only recommend pytidycensus functions and geographic levels.
""",
            }
        )

        return await self.llm_manager.chat_completion(messages)

    async def _handle_general_discussion(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle general discussion or clarifications."""
        messages = self.conversation.get_context_messages()
        return await self.llm_manager.chat_completion(messages)

    async def _search_census_variables(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Search for Census variables related to concepts."""
        suggestions = []

        for concept in concepts:
            # First, try knowledge base for common topics
            kb_variables = get_variables_for_topic(concept)
            if kb_variables:
                for var_name, var_codes in kb_variables.items():
                    if isinstance(var_codes, str):
                        var_codes = [var_codes]
                    elif isinstance(var_codes, list):
                        # Handle multiple codes for same concept
                        pass
                    else:
                        var_codes = [str(var_codes)]

                    for code in var_codes:
                        suggestions.append(
                            {
                                "name": code,
                                "concept": concept,
                                "code": code,
                                "label": var_name.replace("_", " ").title(),
                                "description": f"From pytidycensus knowledge base for {concept}",
                                "source": "knowledge_base",
                            }
                        )

            # Also try pytidycensus variable search for additional results
            try:
                if concept.lower() in self._variable_cache:
                    vars_df = self._variable_cache[concept.lower()]
                else:
                    vars_df = search_variables(concept, 2020, "acs", "acs5")
                    self._variable_cache[concept.lower()] = vars_df

                if not vars_df.empty:
                    # Get top 3 most relevant variables from search
                    top_vars = vars_df.head(3)
                    for _, var in top_vars.iterrows():
                        suggestions.append(
                            {
                                "name": var.get("name", ""),
                                "concept": concept,
                                "code": var.get("name", ""),
                                "label": var.get("label", ""),
                                "description": var.get("concept", ""),
                                "source": "search",
                            }
                        )

            except Exception as e:
                logger.warning(f"Variable search failed for '{concept}': {e}")

        # NEW APPROACH: Use selective normalization based on specific variable codes and labels
        # Extract all variable codes and labels from suggestions
        var_codes = [s["code"] for s in suggestions]
        var_labels = [s.get("label", "") for s in suggestions]

        # Get normalization variables for the specific codes (only if they need normalization)
        normalization_vars = get_normalization_variables_for_codes(var_codes, var_labels)

        # Add normalization variables to suggestions
        # normalization_vars is a dict of {denominator_code: description}
        for denom_code, denom_name in normalization_vars.items():
            suggestions.append(
                {
                    "name": denom_code,
                    "concept": "normalization",
                    "code": denom_code,
                    "label": denom_name.replace("_", " ").title() + " (DENOMINATOR)",
                    "description": f"Normalization variable - REQUIRED for rates/percentages",
                    "source": "selective_normalization",
                }
            )

        return suggestions[:25]  # Limit to prevent overwhelming the LLM

    async def _execute_census_query(self) -> str:
        """Execute the Census query and return results."""
        try:
            # Generate pytidycensus code
            code = self._generate_pytidycensus_code()

            if not self.census_api_key:
                return f"""
I've prepared your Census data query! Here's the pytidycensus code:

```python
{code}
```

To run this, you'll need a Census API key. Get one free at: https://api.census.gov/data/key_signup.html

Then either:
1. Set environment variable: `export CENSUS_API_KEY="your_key_here"`
2. Pass it to the function: `api_key="your_key_here"`

This query will get you:
- **Variables**: {', '.join(self.conversation.state.variables)}
- **Geography**: {self.conversation.state.geography}
- **Location**: {self.conversation.state.state or 'All areas'}
- **Year**: {self.conversation.state.year or 2020}

The result will be a pandas DataFrame with {self.conversation.state.output_format} format.
"""

            # Actually execute the query (always use wide format)
            if self.conversation.state.dataset == "decennial":
                data = tc.get_decennial(
                    geography=self.conversation.state.geography,
                    variables=self.conversation.state.variables,
                    state=self.conversation.state.state,
                    county=self.conversation.state.county,
                    year=self.conversation.state.year or 2020,
                    output="wide",  # Always use wide format
                    api_key=self.census_api_key,
                )
            else:
                data = tc.get_acs(
                    geography=self.conversation.state.geography,
                    variables=self.conversation.state.variables,
                    state=self.conversation.state.state,
                    county=self.conversation.state.county,
                    year=self.conversation.state.year or 2020,
                    output="wide",  # Always use wide format
                    api_key=self.census_api_key,
                )

            # Clean up variable names by removing 'E' suffix
            data = self._clean_variable_names(data)

            # Update state with results
            self.conversation.state.data_shape = f"{data.shape[0]} rows × {data.shape[1]} columns"
            self.conversation.state.generated_code = code

            return f"""
✅ Success! I retrieved your Census data:

**Results**: {data.shape[0]} rows × {data.shape[1]} columns
**Data preview:**
{data.head().to_string()}

**Generated code:**
```python
{code}
```

The data is now ready for analysis. Would you like me to:
1. Explain any specific columns?
2. Suggest visualizations?
3. Help with additional analysis?
"""

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return f"""
I encountered an error executing your query: {str(e)}

Here's the code I was trying to run:
```python
{self._generate_pytidycensus_code()}
```

This might help:
1. Check that all parameters are correct
2. Verify your Census API key is valid
3. Some geographies may not be available for all variables

Would you like to adjust the query parameters?
"""

    def _generate_pytidycensus_code(self) -> str:
        """Generate pytidycensus code from current state."""
        state = self.conversation.state

        # Determine function to use
        if state.dataset == "decennial":
            func = "tc.get_decennial"
        else:
            func = "tc.get_acs"

        # Build parameters
        params = [
            f'geography="{state.geography}"',
            f"variables={state.variables}",
        ]

        if state.state:
            params.append(f'state="{state.state}"')
        if state.county:
            params.append(f'county="{state.county}"')
        if state.year:
            params.append(f"year={state.year}")
        # Always use wide format
        params.append('output="wide"')
        if state.geometry:
            params.append("geometry=True")

        params.append("api_key=census_api_key")

        # Format code
        params_str = ",\n    ".join(params)
        code = f"""import pytidycensus as tc

# Set your Census API key
# Get one at: https://api.census.gov/data/key_signup.html
census_api_key = "YOUR_API_KEY_HERE"

# Get Census data (wide format with cleaned variable names)
data = {func}(
    {params_str}
)

# Clean variable names by removing 'E' suffix
column_mapping = {{col: col[:-1] for col in data.columns
                  if col.endswith('E') and '_' in col and col.split('_')[0].startswith('B')}}
if column_mapping:
    data = data.rename(columns=column_mapping)
    print(f"Cleaned {{len(column_mapping)}} variable names by removing 'E' suffix")

print(f"Retrieved {{data.shape[0]}} rows and {{data.shape[1]}} columns")
print(data.head())"""

        return code

    def _clean_variable_names(self, data):
        """Clean up variable names by removing 'E' suffix from Census variable codes."""

        # Create a mapping of old column names to new names
        column_mapping = {}
        for col in data.columns:
            # Only rename Census variable columns (pattern: B#####_###E)
            if isinstance(col, str) and col.endswith("E") and "_" in col:
                # Check if it looks like a Census variable code
                parts = col.split("_")
                if len(parts) == 2 and parts[0].startswith("B") and parts[1].endswith("E"):
                    # Remove the 'E' suffix: B19013_001E -> B19013_001
                    new_name = col[:-1]
                    column_mapping[col] = new_name

        # Rename the columns
        if column_mapping:
            data = data.rename(columns=column_mapping)
            logger.info(f"Cleaned {len(column_mapping)} variable names by removing 'E' suffix")

        return data

    def reset_conversation(self):
        """Reset the conversation to start fresh."""
        self.conversation.reset()

    def get_conversation_state(self) -> ConversationState:
        """Get current conversation state."""
        return self.conversation.state

    def export_conversation(self) -> str:
        """Export conversation for saving/sharing."""
        return self.conversation.export_state()

    def import_conversation(self, json_data: str):
        """Import a saved conversation."""
        self.conversation.import_state(json_data)
