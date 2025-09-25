"""Command-line interface for Census Assistant.

Simple CLI for interactive Census data discovery.
"""

import argparse
import asyncio
import os
import sys

from .assistant import CensusAssistant


def print_welcome():
    """Print welcome message."""
    print(
        """
🏛️  Welcome to Census Assistant! 🏛️

I'll help you find and retrieve US Census data using natural language.
Just tell me what you're researching!

Examples:
- "I'm studying income inequality in California"
- "I need population data by race for Chicago"
- "Show me median rent in urban areas"

Type 'help' for commands, 'quit' to exit.
"""
    )


def print_help():
    """Print help information."""
    print(
        """
Census Assistant Commands:
- 'help': Show this help message
- 'quit' or 'exit': Exit the assistant
- 'reset': Start a new conversation
- 'state': Show current conversation state
- 'export': Export conversation to JSON

For Census data help:
- Tell me your research topic in natural language
- I'll help you find the right variables and geographic level
- When ready, I'll generate and run the query for you

API Keys:
- Census API: Get free key at https://api.census.gov/data/key_signup.html
- OpenAI (optional): For better LLM responses
- Or use local Ollama models (free, requires setup)
"""
    )


async def main():
    """Main CLI loop."""
    parser = argparse.ArgumentParser(description="Census Assistant CLI")
    parser.add_argument("--census-key", help="Census API key")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--non-interactive", action="store_true", help="Non-interactive mode")

    args = parser.parse_args()

    # Get API keys from environment if not provided
    census_key = args.census_key or os.getenv("CENSUS_API_KEY")
    openai_key = args.openai_key or os.getenv("OPENAI_API_KEY")

    # Initialize assistant
    try:
        assistant = CensusAssistant(census_api_key=census_key, openai_api_key=openai_key)
    except Exception as e:
        print(f"Error initializing assistant: {e}")
        print("\nTroubleshooting:")
        print("1. Install required packages: pip install openai ollama")
        print("2. For local models: install Ollama and run 'ollama pull llama3.2'")
        print("3. For cloud models: set OPENAI_API_KEY environment variable")
        sys.exit(1)

    if args.non_interactive:
        print("Non-interactive mode not yet implemented.")
        return

    print_welcome()

    # Main conversation loop
    try:
        while True:
            try:
                user_input = input("\n📊 You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ["quit", "exit"]:
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == "help":
                    print_help()
                    continue
                elif user_input.lower() == "reset":
                    assistant.reset_conversation()
                    print("🔄 Conversation reset. What would you like to research?")
                    continue
                elif user_input.lower() == "state":
                    state = assistant.get_conversation_state()
                    print(f"\n📋 Current state:")
                    print(f"Research question: {state.research_question}")
                    print(f"Variables: {state.variables}")
                    print(f"Geography: {state.geography}")
                    print(f"State: {state.state}")
                    print(f"Year: {state.year}")
                    print(f"Ready for execution: {state.is_ready_for_execution()}")
                    continue
                elif user_input.lower() == "export":
                    exported = assistant.export_conversation()
                    filename = f"census_conversation_{int(asyncio.get_event_loop().time())}.json"
                    with open(filename, "w") as f:
                        f.write(exported)
                    print(f"💾 Conversation exported to {filename}")
                    continue

                # Process with assistant
                print("\n🤔 Thinking...")
                response = await assistant.chat(user_input)
                print(f"\n🏛️  Assistant: {response}")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                print("Please try again or type 'help' for assistance.")

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


def run_cli():
    """Entry point for CLI."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    run_cli()
