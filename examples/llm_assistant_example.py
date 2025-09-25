"""
Example: Using the Census LLM Assistant

This example demonstrates the conversational interface to Census data using
real conversation patterns from the test suite. Shows wide format output,
variable name cleaning, and selective normalization.
"""

import asyncio
import os

from pytidycensus.llm_interface import CensusAssistant


async def wisconsin_income_example():
    """Example: Wisconsin County Income Analysis (from test suite)."""

    # Initialize the assistant
    assistant = CensusAssistant(
        census_api_key=os.getenv("CENSUS_API_KEY"), openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("🏛️  Wisconsin County Income Analysis")
    print("=" * 50)
    print("This example shows wide format output with cleaned variable names\n")

    # Realistic conversation from test suite
    conversations = [
        "I'm studying household income variations in Wisconsin",
        "I want county-level data",
        "Use the most recent data available",
        "Generate the pytidycensus code",
    ]

    for i, user_message in enumerate(conversations, 1):
        print(f"👤 User ({i}): {user_message}")
        print("🤔 Processing...")

        response = await assistant.chat(user_message)
        print(f"🏛️  Assistant: {response[:200]}...")  # Truncate for readability

        # Show state progression
        state = assistant.get_conversation_state()
        state_info = []
        if state.geography:
            state_info.append(f"geography={state.geography}")
        if state.variables:
            var_display = state.variables[:2] + (["..."] if len(state.variables) > 2 else [])
            state_info.append(f"variables={var_display}")
        if state.state:
            state_info.append(f"state={state.state}")
        if state.year:
            state_info.append(f"year={state.year}")

        if state_info:
            print(f"📋 State: {', '.join(state_info)}")

        print("─" * 50)

    print(f"\n✅ Final Result:")
    print(f"   - Geography: {state.geography}")
    print(f"   - Variables: {state.variables}")
    print(f"   - Output format: wide (always)")
    print(f"   - Column names: B19013_001 (E suffix removed)")
    print(f"   - Ready for execution: {state.is_ready_for_execution()}")


async def dc_inequality_example():
    """Example: DC Inequality with Normalization (from test suite)."""

    assistant = CensusAssistant(
        census_api_key=os.getenv("CENSUS_API_KEY"), openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("\n🏛️  DC Inequality Analysis with Selective Normalization")
    print("=" * 60)
    print("This example shows how selective normalization works\n")

    conversations = [
        "I want to study inequality in Washington DC",
        "Get poverty and income data by Census tract",
        "Include both counts and totals for calculating rates",
        "Use 2020 ACS 5-year data",
        "Yes, generate the code",
    ]

    for i, user_message in enumerate(conversations, 1):
        print(f"👤 User ({i}): {user_message}")
        response = await assistant.chat(user_message)
        print(f"🏛️  Assistant: {response[:150]}...")

        state = assistant.get_conversation_state()
        if state.variables:
            print(f"📋 Variables: {state.variables}")
        print("─" * 40)

    print(f"\n✅ Selective Normalization Demo:")
    variables = state.variables or []
    for var in variables:
        if "B17001_002" in var:
            print(f"   • {var} (poverty count) → Gets B17001_001E (total)")
        elif "B17001_001" in var:
            print(f"   • {var} (poverty total) → This IS the denominator")
        elif "B19013_001" in var:
            print(f"   • {var} (median income) → NO denominator (already a median)")

    print(f"\n📊 Clean Output Columns:")
    for var in variables:
        if var.endswith("E"):
            clean_name = var[:-1]
            print(f"   • {var} → {clean_name}")


async def spatial_mapping_example():
    """Example: Spatial Analysis with Geometry."""

    assistant = CensusAssistant(
        census_api_key=os.getenv("CENSUS_API_KEY"), openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print("\n🏛️  Spatial Mapping Example")
    print("=" * 40)
    print("Shows geometry=True for mapping applications\n")

    conversations = [
        "I need Wisconsin county income data for mapping",
        "Include geographic boundaries",
        "2020 ACS data",
        "Generate the mapping-ready code",
    ]

    for i, user_message in enumerate(conversations, 1):
        print(f"👤 User ({i}): {user_message}")
        response = await assistant.chat(user_message)
        print(f"🏛️  Assistant: {response[:120]}...")
        print("─" * 30)

    state = assistant.get_conversation_state()
    print(f"\n✅ Mapping-Ready Configuration:")
    print(f"   • Geography: {state.geography}")
    print(f"   • Geometry: {state.geometry}")
    print(f"   • Output: GeoPandas GeoDataFrame")
    print(f"   • Ready for: data.plot(column='B19013_001')")


async def quick_query_example():
    """Example of a direct, single-request query."""

    assistant = CensusAssistant()

    print("\n🚀 Direct Query Example")
    print("=" * 30)
    print("Shows immediate execution for clear requests\n")

    # Direct, specific request
    response = await assistant.chat("Get me total population by state for 2020 decennial census")

    print(f"👤 User: Get me total population by state for 2020 decennial census")
    print(f"🏛️  Assistant: {response[:300]}...")

    print(f"\n✅ Key Features Demonstrated:")
    print(f"   • Direct execution without multi-turn conversation")
    print(f"   • Wide format output automatically applied")
    print(f"   • Variable name cleaning (P1_001N → P1_001)")
    print(f"   • Complete pytidycensus code generation")


async def normalization_comparison_demo():
    """Demonstrate selective normalization in action."""

    print("\n🧠 Selective Normalization Intelligence Demo")
    print("=" * 50)
    print("Shows which variables get normalization and which don't\n")

    from pytidycensus.llm_interface.knowledge_base import needs_normalization

    test_variables = [
        ("B19013_001E", "Median household income"),
        ("B25064_001E", "Median gross rent"),
        ("B08301_021E", "Workers who walked to work"),
        ("B25003_002E", "Owner-occupied housing units"),
        ("B08006_008E", "Mean travel time to work"),
        ("B25119_001E", "Housing cost as percentage of income"),
        ("B19001_017E", "Households with income $200,000+"),
        ("B17001_001E", "Total population for poverty status"),
    ]

    print("Variable Analysis:")
    print("-" * 70)
    print("Variable Code    | Description                    | Needs Norm?")
    print("-" * 70)

    for var_code, description in test_variables:
        needs_norm = needs_normalization(var_code, description)
        status = "✅ YES" if needs_norm else "❌ NO "
        reason = ""

        if "median" in description.lower() or "mean" in description.lower():
            reason = "(already a rate/average)"
        elif "percentage" in description.lower():
            reason = "(already a percentage)"
        elif var_code.endswith("_001E"):
            reason = "(this IS the total)"
        elif needs_norm:
            reason = "(count needs denominator)"

        print(f"{var_code:<15} | {description:<30} | {status} {reason}")

    print("\n🎯 Intelligence Summary:")
    print("   • Medians/means/rates → No normalization needed")
    print("   • Count variables → Get appropriate denominators")
    print("   • Total variables (_001E) → These ARE the denominators")
    print("   • Result: Clean analysis without suggestion overload")


def setup_instructions():
    """Print comprehensive setup instructions."""
    print(
        """
🛠️  Setup Instructions for Census LLM Assistant

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

3. Key Features Showcased in Examples:
   • Wide format output (always enabled)
   • Variable name cleaning (B19013_001E → B19013_001)
   • Selective normalization (smart denominator suggestions)
   • Real conversation patterns from test suite
   • Generated pytidycensus code

4. Run examples:
   python examples/llm_assistant_example.py

   Or interactive CLI:
   python -m pytidycensus.llm_interface.cli

   Or test conversations:
   python tests/test_conversation_to_query.py verbose
    """
    )


async def main():
    """Run comprehensive examples showcasing LLM assistant features."""
    setup_instructions()

    # Check if we can run examples
    try:
        CensusAssistant()
        print("✅ LLM providers available! Running examples...\n")

        # Run the updated examples showcasing new features
        await wisconsin_income_example()
        await dc_inequality_example()
        await spatial_mapping_example()
        await quick_query_example()

        # Show normalization intelligence (doesn't require LLM)
        normalization_comparison_demo()

        print("\n" + "=" * 60)
        print("🎉 All examples completed!")
        print("\nKey improvements demonstrated:")
        print("• Wide format DataFrames with clean column names")
        print("• Intelligent normalization suggestions")
        print("• Real conversation patterns from test suite")
        print("• Production-ready pytidycensus code generation")

    except Exception as e:
        print(f"❌ Cannot run examples: {e}")
        print("\nPlease follow setup instructions above.")
        print("Note: You can still run the normalization demo without LLM setup:")
        normalization_comparison_demo()


if __name__ == "__main__":
    asyncio.run(main())
