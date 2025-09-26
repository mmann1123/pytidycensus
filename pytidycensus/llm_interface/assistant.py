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
- SPATIAL/MAPPING needs (if user mentions: map, mapping, spatial, boundaries, visualization, plot, choropleth, GIS, explore, visualize, geographic patterns)

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
        "year": 2020,
        "geometry": true_if_spatial_keywords_detected
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
        """Generate appropriate response based on conversation stage and intent analysis."""
        intent = intent_analysis.get("intent", "clarifying")
        current_stage = self.conversation.state.stage

        # Check if user is explicitly asking to execute/generate code
        if intent in ["ready", "execute"] and self.conversation.state.is_ready_for_execution():
            self.conversation.update_state({"stage": "executed"})
            return await self._execute_census_query()

        # Stage-based conversation flow
        if current_stage == "initial":
            return await self._handle_initial_stage(intent_analysis)
        elif current_stage == "clarifying":
            return await self._handle_clarifying_stage(intent_analysis)
        elif current_stage == "variables":
            return await self._handle_variables_stage(intent_analysis)
        elif current_stage == "geography":
            return await self._handle_geography_stage(intent_analysis)
        elif current_stage == "ready":
            return await self._handle_ready_stage(intent_analysis)
        else:
            # Fallback to intent-based handling for backwards compatibility
            return await self._handle_general_discussion(intent_analysis)

    async def _handle_initial_stage(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle initial conversation stage - gather research topic."""
        extracted_info = intent_analysis.get("extracted_info", {})

        # If we extracted research topic, move to variables stage
        if extracted_info.get("variables_mentioned"):
            self.conversation.update_state({"stage": "variables"})
            return await self._handle_variables_stage(intent_analysis)

        # Otherwise, ask for research topic clarification
        self.conversation.update_state({"stage": "clarifying"})
        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
This user is starting a new Census data research project. Analysis: {json.dumps(intent_analysis, indent=2)}

IMPORTANT: We need to systematically gather information in this order:
1. Research topic/variables (CURRENT STAGE)
2. Geographic level
3. Location specifics
4. Time period
5. Execute query

Please:
1. Acknowledge their interest
2. Ask specifically what census variables/topics they need (income, population, housing, education, etc.)
3. Do NOT ask about geography yet - focus only on variables/topic first
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

    async def _handle_clarifying_stage(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle clarifying stage - ensure we have research topic/variables."""
        extracted_info = intent_analysis.get("extracted_info", {})

        # If we now have variables mentioned, move to variables stage
        if extracted_info.get("variables_mentioned"):
            self.conversation.update_state({"stage": "variables"})
            return await self._handle_variables_stage(intent_analysis)

        # Still need clarification on research topic
        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
The user is still clarifying their research needs. Analysis: {json.dumps(intent_analysis, indent=2)}

STAGE: Clarifying research topic (1/5)
NEXT STAGES: variables → geography → location → time → execute

Please help them specify what Census data they need:
1. Ask about specific topics: income, poverty, population, housing, education, employment, etc.
2. Give examples of common research questions
3. Do NOT ask about geography yet - we need variables first
4. Be encouraging and helpful
""",
            }
        )
        return await self.llm_manager.chat_completion(messages)

    async def _handle_variables_stage(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle variables stage - confirm variables and move to geography."""
        extracted_info = intent_analysis.get("extracted_info", {})
        variables_mentioned = extracted_info.get("variables_mentioned", [])

        if variables_mentioned:
            # Search for relevant Census variables
            variable_suggestions = await self._search_census_variables(variables_mentioned)

            # Check if we have enough variables to proceed
            if variable_suggestions:
                self.conversation.update_state({"stage": "geography"})
                messages = self.conversation.get_context_messages()
                messages.append(
                    {
                        "role": "user",
                        "content": f"""
Variables stage complete! Found variables: {json.dumps(variable_suggestions, indent=2)}

STAGE: Geographic level selection (2/5)
COMPLETED: ✅ Variables identified
NEXT STAGES: location → time → execute

Now we need to determine geographic level. Please:
1. Suggest appropriate variables for their research
2. Show calculation examples if rates/percentages needed
3. THEN ask specifically about geographic level (state, county, tract, etc.)
4. Explain tradeoffs between geographic levels (detail vs sample size)
5. Do NOT ask about specific locations yet - focus on geographic LEVEL first
""",
                    }
                )
                return await self.llm_manager.chat_completion(messages)

        # Still working on variables
        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
Working on variables identification. Analysis: {json.dumps(intent_analysis, indent=2)}

STAGE: Variable selection (2/5)
NEXT STAGES: geography → location → time → execute

Please help refine their variable needs:
1. Acknowledge their research topic
2. Suggest specific Census variables that match their needs
3. Show calculation examples if needed
4. Do NOT ask about geography yet - ensure variables are solid first
""",
            }
        )
        return await self.llm_manager.chat_completion(messages)

    async def _handle_geography_stage(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle geography stage - ensure geographic level is specified before location."""
        extracted_info = intent_analysis.get("extracted_info", {})
        current_geo = self.conversation.state.geography

        # If geography level is now specified, move to location requirements
        if current_geo or extracted_info.get("geography_mentioned"):
            if extracted_info.get("geography_mentioned"):
                self.conversation.update_state({"geography": extracted_info["geography_mentioned"]})
                current_geo = extracted_info["geography_mentioned"]

            # Check if this geography level requires location specification
            if current_geo in ["county", "tract", "block group", "block"]:
                self.conversation.update_state({"stage": "ready"})
                messages = self.conversation.get_context_messages()
                messages.append(
                    {
                        "role": "user",
                        "content": f"""
Geographic level set to {current_geo}!

STAGE: Location specification (3/5)
COMPLETED: ✅ Variables ✅ Geographic level ({current_geo})
NEXT STAGES: time → execute

{current_geo} level requires state specification. Please:
1. Ask which state they want to analyze
2. If {current_geo} level, also ask for county if needed
3. Give examples like "Wisconsin", "WI", or "55"
4. Do NOT ask about time period yet - get location first
""",
                    }
                )
                return await self.llm_manager.chat_completion(messages)
            else:
                # State or national level - ready for time/execution
                self.conversation.update_state({"stage": "ready"})
                return await self._handle_ready_stage(intent_analysis)

        # Still need geographic level
        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
Need geographic level specification. Analysis: {json.dumps(intent_analysis, indent=2)}

STAGE: Geographic level (3/5)
COMPLETED: ✅ Variables
NEXT STAGES: location → time → execute

Please help them choose geographic level:
1. Explain options: state, county, tract, block group, etc.
2. Explain tradeoffs (detail vs sample size)
3. Ask specifically which geographic level they need
4. Do NOT ask about specific states/counties yet - just the LEVEL
""",
            }
        )
        return await self.llm_manager.chat_completion(messages)

    async def _handle_ready_stage(self, intent_analysis: Dict[str, Any]) -> str:
        """Handle ready stage - final details before execution."""
        missing = self.conversation.state.get_missing_info()

        if not missing:
            # Ready to execute!
            messages = self.conversation.get_context_messages()
            messages.append(
                {
                    "role": "user",
                    "content": f"""
All information collected! Ready to generate code.

STAGE: Ready for execution (5/5)
COMPLETED: ✅ Variables ✅ Geography ✅ Location ✅ Time

Current state: {json.dumps(self.conversation.state.to_dict(), indent=2)}

Please:
1. Summarize what data will be retrieved
2. Ask if they want to proceed with code generation
3. Mention that code will use wide format and clean variable names
""",
                }
            )
            return await self.llm_manager.chat_completion(messages)

        # Still missing some information
        if "state" in missing:
            messages = self.conversation.get_context_messages()
            messages.append(
                {
                    "role": "user",
                    "content": f"""
Need state specification for {self.conversation.state.geography} level data.

STAGE: Location details (4/5)
COMPLETED: ✅ Variables ✅ Geographic level
MISSING: State specification

Please ask which state they want to analyze. Give examples like "Wisconsin", "WI", or "55".
""",
                }
            )
            return await self.llm_manager.chat_completion(messages)

        if "year" in missing:
            messages = self.conversation.get_context_messages()
            messages.append(
                {
                    "role": "user",
                    "content": f"""
Need time period specification.

STAGE: Time period (4/5)
COMPLETED: ✅ Variables ✅ Geography ✅ Location
MISSING: Year

Please ask what year they need. Suggest recent years like 2020-2022 for ACS data.
""",
                }
            )
            return await self.llm_manager.chat_completion(messages)

        # Other missing info
        messages = self.conversation.get_context_messages()
        messages.append(
            {
                "role": "user",
                "content": f"""
Still need some information: {missing}

Please ask for the missing details to complete their request.
""",
            }
        )
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

        # Add mapping code if geometry is enabled
        if state.geometry:
            code += f"""

# Create interactive map (geometry=True gives you a GeoPandas GeoDataFrame)
# No external shapefiles needed - pytidycensus handles it automatically!
data.explore(
    column='{state.variables[0][:-1] if state.variables and state.variables[0].endswith('E') else (state.variables[0] if state.variables else 'value')}',  # Use cleaned variable name
    legend=True,
    cmap='OrRd',  # Color scheme
    tooltip=True
)
# Alternative: Static plot with matplotlib
# data.plot(column='{state.variables[0][:-1] if state.variables and state.variables[0].endswith('E') else (state.variables[0] if state.variables else 'value')}', legend=True)"""

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
