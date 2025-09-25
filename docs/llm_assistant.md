# Census LLM Assistant

The Census LLM Assistant provides a conversational interface to US Census data using Large Language Models. Instead of learning Census variable codes and geography hierarchies, you can describe your research needs in natural language.

## Quick Start

```python
import asyncio
from pytidycensus.llm_interface import CensusAssistant

async def main():
    # Initialize assistant
    assistant = CensusAssistant(
        census_api_key="your_census_api_key",
        openai_api_key="your_openai_key"  # Optional
    )

    # Have a conversation
    response = await assistant.chat("I need median income by race in California cities")
    print(response)

asyncio.run(main())
```

## Installation

### Basic Installation
```bash
pip install pytidycensus
```

### LLM Dependencies
Choose one or both:

**Option A: OpenAI (Recommended for reliability)**
```bash
pip install openai
export OPENAI_API_KEY="your_key_here"
```

**Option B: Local Models (Free, requires setup)**
```bash
pip install ollama
# Install Ollama from https://ollama.ai/
ollama pull llama3.2
ollama serve
```

### Census API Key
Get a free Census API key:
```bash
# Get key at: https://api.census.gov/data/key_signup.html
export CENSUS_API_KEY="your_census_key_here"
```

## Usage Patterns

### 1. Guided Data Discovery

Let the assistant guide you through finding the right data:

```python
assistant = CensusAssistant()

# Start with a general topic
await assistant.chat("I'm studying housing affordability")

# Assistant will ask clarifying questions:
# - What geographic area?
# - What specific metrics?
# - What time period?

# Answer naturally
await assistant.chat("California cities, median rent vs median income, latest data")

# Assistant will suggest variables and generate code
await assistant.chat("Yes, run the query")
```

### 2. Direct Requests

Make specific requests directly:

```python
response = await assistant.chat(
    "Get total population by state from 2020 decennial census"
)

# Assistant will:
# 1. Identify variables (P1_001N for total population)
# 2. Set geography (state level)
# 3. Choose dataset (decennial 2020)
# 4. Generate and execute pytidycensus code
```

### 3. Variable Discovery

Get help finding the right Census variables:

```python
await assistant.chat("What variables are available for poverty data?")

# Assistant will search and explain:
# - B17001_002E: Poverty status by age (under poverty line)
# - B17001_001E: Total for poverty status determination
# - B17020_002E: Poverty status by age (children under 5)
# etc.
```

### 4. Geographic Guidance

Understand geography options:

```python
await assistant.chat("I need neighborhood-level data for Chicago")

# Assistant will explain:
# - Tract level: ~600 areas in Chicago (good for neighborhood analysis)
# - Block group level: ~3000 areas (very detailed, small sample sizes)
# - Place level: City of Chicago as one unit (not neighborhood-level)
# And help you choose the right level for your research
```

## Command Line Interface

For interactive exploration:

```bash
# Start interactive session
python -m pytidycensus.llm_interface.cli

# With API keys
python -m pytidycensus.llm_interface.cli --census-key YOUR_KEY --openai-key YOUR_KEY
```

Commands in CLI:
- `help`: Show help information
- `reset`: Start new conversation
- `state`: Show current conversation state
- `export`: Save conversation to JSON
- `quit`: Exit

## Configuration Options

### LLM Provider Priority

The assistant tries providers in order:
1. **OpenAI GPT-3.5 Turbo** (reliable, ~$0.01 per conversation)
2. **Local Ollama** (free, requires local setup)

### Custom Configuration

```python
from pytidycensus.llm_interface import LLMManager, OpenAIProvider, OllamaProvider

# Create custom provider setup
providers = [
    OpenAIProvider(model="gpt-4", api_key="your_key"),
    OllamaProvider(model="mixtral:8x7b")  # Larger local model
]

llm_manager = LLMManager(providers)
assistant = CensusAssistant(llm_manager=llm_manager)
```

## Example Conversations

### Housing Research
```
User: I'm researching housing costs in expensive cities