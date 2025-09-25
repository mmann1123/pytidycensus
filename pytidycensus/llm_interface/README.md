# Census LLM Assistant

A conversational interface to US Census data using Large Language Models.

## Quick Start

```python
import asyncio
from pytidycensus.llm_interface import CensusAssistant

async def main():
    assistant = CensusAssistant(
        census_api_key="your_census_key",
        openai_api_key="your_openai_key"  # or use local Ollama
    )

    response = await assistant.chat("I need median income data for California cities")
    print(response)

asyncio.run(main())
```

## Installation Options

### Option 1: OpenAI (Reliable, ~$0.01/conversation)
```bash
pip install openai
export OPENAI_API_KEY="your_key"
```

### Option 2: Local Ollama (Free, requires setup)
```bash
pip install ollama
# Install from https://ollama.ai/
ollama pull llama3.2
ollama serve
```

### Census API Key (Required for data)
```bash
# Get free key: https://api.census.gov/data/key_signup.html
export CENSUS_API_KEY="your_census_key"
```

## Features

- **Natural Language**: Describe research needs in plain English
- **Variable Discovery**: Finds relevant Census variables automatically
- **Geography Guidance**: Helps choose appropriate geographic levels
- **Code Generation**: Produces working pytidycensus code
- **Data Execution**: Can run queries and return results
- **Cost Effective**: Uses cheap models with local fallback

## Command Line
```bash
python -m pytidycensus.llm_interface.cli
```

## Example Conversations

"I'm studying housing affordability in major cities" →
- Suggests median rent and income variables
- Recommends place-level geography for cities
- Generates code to retrieve and analyze data

"What poverty data is available?" →
- Searches Census variable catalog
- Explains different poverty measures
- Shows specific variable codes and descriptions

## Architecture

- **Providers**: Pluggable LLM backends (OpenAI, Ollama, etc.)
- **Conversation**: Stateful dialog management
- **Assistant**: Main orchestration and Census domain logic
- **CLI**: Interactive command-line interface