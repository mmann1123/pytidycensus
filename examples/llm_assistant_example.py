"""
Example: Using the Census LLM Assistant

This example shows how to use the LLM-driven interface for Census data discovery.
"""

import asyncio
import os

from pytidycensus.llm_interface import CensusAssistant


async def example_conversation():
    """Example conversation with the Census Assistant."""

    # Initialize the assistant
    # Will use OpenAI if API key available, otherwise falls back to local Ollama
    assistant = CensusAssistant(
        census_api_key=os.getenv("CENSUS_API_KEY"), openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("🏛️  Census Assistant Example\n")
    print("=" * 50)

    # Example conversation flow
    conversations = [
        "I'm researching housing affordability in California cities",
        "I want to compare median rent and median income",
        "Use city-level data for 2022",
        "Yes, generate the code and run it",
    ]

    for i, user_message in enumerate(conversations, 1):
        print(f"\n👤 User ({i}): {user_message}")
        print("🤔 Processing...")

        response = await assistant.chat(user_message)
        print(f"\n🏛️  Assistant: {response}")

        # Show current state
        state = assistant.get_conversation_state()
        if state.variables or state.geography:
            print(f"\n📋 Current state:")
            print(f"   Variables: {state.variables}")
            print(f"   Geography: {state.geography}")
            print(f"   State: {state.state}")
            print(f"   Ready: {state.is_ready_for_execution()}")

        print("\n" + "─" * 50)

    # Export the conversation
    exported = assistant.export_conversation()
    print(f"\n💾 Conversation exported ({len(exported)} characters)")


async def quick_query_example():
    """Example of a quick, direct query."""

    assistant = CensusAssistant()

    print("\n🚀 Quick Query Example")
    print("=" * 30)

    # Direct, specific request
    response = await assistant.chat("Get me total population by state for 2020 decennial census")

    print(f"Response: {response}")


async def variable_discovery_example():
    """Example focusing on variable discovery."""

    assistant = CensusAssistant()

    print("\n🔍 Variable Discovery Example")
    print("=" * 35)

    # Help user discover variables
    queries = [
        "I need data about poverty",
        "What about poverty by age groups?",
        "Show me the specific variable codes",
    ]

    for query in queries:
        print(f"\n👤 User: {query}")
        response = await assistant.chat(query)
        print(f"🏛️  Assistant: {response[:200]}...")  # Truncate for example


def setup_instructions():
    """Print setup instructions."""
    print(
        """
🛠️  Setup Instructions:

1. Census API Key (required for data retrieval):
   - Get free key: https://api.census.gov/data/key_signup.html
   - Set: export CENSUS_API_KEY="your_key_here"

2. LLM Options (choose one):

   Option A - OpenAI (reliable, costs ~$0.01 per conversation):
   - pip install openai
   - Set: export OPENAI_API_KEY="your_key_here"

   Option B - Local Ollama (free, requires setup):
   - Install Ollama: https://ollama.ai/
   - Run: ollama pull llama3.2
   - Start: ollama serve

3. Run examples:
   python examples/llm_assistant_example.py

   Or use CLI:
   python -m pytidycensus.llm_interface.cli
    """
    )


async def main():
    """Run all examples."""
    setup_instructions()

    # Check if we can run examples
    try:
        CensusAssistant()
        print("✅ LLM providers available!")

        # Run examples
        await example_conversation()
        await quick_query_example()
        await variable_discovery_example()

    except Exception as e:
        print(f"❌ Cannot run examples: {e}")
        print("\nPlease follow setup instructions above.")


if __name__ == "__main__":
    asyncio.run(main())
