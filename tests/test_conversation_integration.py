"""Simple integration tests for conversation-to-query functionality.

These tests focus on verifying that the conversation system correctly
generates pytidycensus code based on conversation state, without complex
LLM mocking.
"""

import pytest

from pytidycensus.llm_interface import CensusAssistant


def show_conversation_state(assistant, test_name, description=""):
    """Display current conversation state for debugging."""
    print(f"\n=== {test_name} ===")
    if description:
        print(f"Description: {description}")

    state = assistant.conversation.state
    print("Current conversation state:")

    state_info = []
    if state.geography:
        state_info.append(f"  Geography: {state.geography}")
    if state.variables:
        state_info.append(
            f"  Variables: {state.variables[:3]}{'...' if len(state.variables) > 3 else ''}"
        )
    if state.state:
        state_info.append(f"  State: {state.state}")
    if state.county:
        state_info.append(f"  County: {state.county}")
    if state.year:
        state_info.append(f"  Year: {state.year}")
    if state.dataset:
        state_info.append(f"  Dataset: {state.dataset}")
    if state.geometry:
        state_info.append(f"  Geometry: {state.geometry}")
    if state.output_format:
        state_info.append(f"  Output format: {state.output_format}")

    if state_info:
        print("\n".join(state_info))
    else:
        print("  (No state set)")

    print("\n--- Generated Code ---")
    try:
        code = assistant._generate_pytidycensus_code()
        print(code)
    except Exception as e:
        print(f"Error generating code: {e}")

    print("=" * 60)


class TestConversationIntegration:
    """Integration tests for conversation system."""

    def test_query_generation_from_state(self):
        """Test that conversation state correctly generates pytidycensus code."""
        assistant = CensusAssistant()

        # Test case 1: Basic ACS query
        assistant.conversation.state.geography = "state"
        assistant.conversation.state.variables = ["B19013_001E"]
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        # Show the conversation state and generated code
        show_conversation_state(
            assistant, "Basic ACS Query Generation", "State-level median household income for 2020"
        )

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        assert 'geography="state"' in code
        assert "B19013_001E" in code
        assert "year=2020" in code
        assert "import pytidycensus as tc" in code

    def test_dc_query_generation(self):
        """Test that DC state queries generate correctly."""
        assistant = CensusAssistant()

        # Set up DC inequality analysis state
        assistant.conversation.state.geography = "tract"
        assistant.conversation.state.variables = ["B17001_002E", "B17001_001E"]
        assistant.conversation.state.state = "DC"
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        # Show the conversation state and generated code
        show_conversation_state(
            assistant,
            "DC Inequality Analysis",
            "Tract-level poverty data for Washington DC with normalization variables",
        )

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        assert 'geography="tract"' in code
        assert 'state="DC"' in code
        assert "B17001_002E" in code
        assert "B17001_001E" in code

    def test_decennial_query_generation(self):
        """Test that decennial Census queries generate correctly."""
        assistant = CensusAssistant()

        # Set up 2020 decennial query
        assistant.conversation.state.geography = "state"
        assistant.conversation.state.variables = ["P1_001N"]
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "decennial"

        # Show the conversation state and generated code
        show_conversation_state(
            assistant,
            "2020 Decennial Census Query",
            "State-level total population from 2020 Census",
        )

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_decennial(" in code
        assert 'geography="state"' in code
        assert "P1_001N" in code
        assert "year=2020" in code

    def test_county_subset_query_generation(self):
        """Test queries with county subsetting."""
        assistant = CensusAssistant()

        # Set up county-level query for specific state
        assistant.conversation.state.geography = "county"
        assistant.conversation.state.variables = ["B19013_001E"]
        assistant.conversation.state.state = "WI"
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        assert 'geography="county"' in code
        assert 'state="WI"' in code
        assert "B19013_001E" in code

    def test_tract_level_query_generation(self):
        """Test tract-level queries with state and county."""
        assistant = CensusAssistant()

        # Set up tract-level query
        assistant.conversation.state.geography = "tract"
        assistant.conversation.state.variables = ["B19013_001E"]
        assistant.conversation.state.state = "WI"
        assistant.conversation.state.county = "Dane"
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        assert 'geography="tract"' in code
        assert 'state="WI"' in code
        assert 'county="Dane"' in code

    def test_geometry_query_generation(self):
        """Test queries that include geometry."""
        assistant = CensusAssistant()

        assistant.conversation.state.geography = "county"
        assistant.conversation.state.variables = ["B19013_001E"]
        assistant.conversation.state.state = "CA"
        assistant.conversation.state.geometry = True
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        # Show the conversation state and generated code
        show_conversation_state(
            assistant,
            "Spatial Data with Geometry",
            "County-level income data for California with geographic boundaries",
        )

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        assert "geometry=True" in code

    def test_wide_output_query_generation(self):
        """Test queries with wide output format."""
        assistant = CensusAssistant()

        assistant.conversation.state.geography = "state"
        assistant.conversation.state.variables = ["B19013_001E", "B01002_001E"]
        assistant.conversation.state.output_format = "wide"
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        assert 'output="wide"' in code

    def test_multiple_variables_generation(self):
        """Test queries with multiple variables."""
        assistant = CensusAssistant()

        assistant.conversation.state.geography = "state"
        assistant.conversation.state.variables = [
            "B19013_001E",  # Median income
            "B17001_002E",  # Below poverty
            "B17001_001E",  # Total for poverty status
            "B01003_001E",  # Total population
        ]
        assistant.conversation.state.year = 2020
        assistant.conversation.state.dataset = "acs5"

        code = assistant._generate_pytidycensus_code()

        assert "tc.get_acs(" in code
        # Check that all variables are included
        for var in assistant.conversation.state.variables:
            assert var in code

    def test_conversation_state_ready_check(self):
        """Test the is_ready_for_execution method."""
        assistant = CensusAssistant()
        state = assistant.conversation.state

        # Initially not ready
        assert not state.is_ready_for_execution()

        # Add required fields
        state.geography = "state"
        state.variables = ["B19013_001E"]

        # Now should be ready
        assert state.is_ready_for_execution()

        # Test tract-level requirements
        state.geography = "tract"
        assert not state.is_ready_for_execution()  # Missing state

        state.state = "CA"
        assert state.is_ready_for_execution()  # Now ready

    def test_conversation_missing_info_detection(self):
        """Test the get_missing_info method."""
        assistant = CensusAssistant()
        state = assistant.conversation.state

        missing = state.get_missing_info()
        assert "variables" in missing
        assert "geography" in missing

        # Add some info
        state.variables = ["B19013_001E"]
        missing = state.get_missing_info()
        assert "variables" not in missing
        assert "geography" in missing

        # Add geography
        state.geography = "tract"
        missing = state.get_missing_info()
        assert "state" in missing  # Tract requires state

        # Complete the requirements
        state.state = "CA"
        missing = state.get_missing_info()
        # Should be empty or only contain optional items
        assert "variables" not in missing
        assert "geography" not in missing

    def test_normalization_variables_included(self):
        """Test that normalization variables are properly suggested."""
        from pytidycensus.llm_interface.knowledge_base import get_normalization_variables

        # Test income normalization
        income_norms = get_normalization_variables("income")
        assert "denominators" in income_norms
        assert "B19001_001E" in income_norms["denominators"].values()  # Total households

        # Test poverty normalization
        poverty_norms = get_normalization_variables("poverty")
        assert "denominators" in poverty_norms
        assert "B17001_001E" in poverty_norms["denominators"].values()  # Total for poverty

        # Test education normalization
        education_norms = get_normalization_variables("education")
        assert "denominators" in education_norms
        assert "B15003_001E" in education_norms["denominators"].values()  # Total 25+

    def test_expected_query_patterns(self):
        """Test that generated queries match expected patterns from documentation."""
        assistant = CensusAssistant()

        # Test case: Wisconsin county income (from docs)
        assistant.conversation.state.geography = "county"
        assistant.conversation.state.variables = ["B19013_001E"]
        assistant.conversation.state.state = "WI"
        assistant.conversation.state.year = 2020

        code = assistant._generate_pytidycensus_code()

        # Should match the pattern from pytidycensus_intro.md
        expected_patterns = [
            "tc.get_acs(",
            'geography="county"',
            "B19013_001E",  # Just check the variable is present
            'state="WI"',
            "year=2020",
        ]

        for pattern in expected_patterns:
            assert pattern in code, f"Expected pattern '{pattern}' not found in:\n{code}"

    def test_code_imports_and_structure(self):
        """Test that generated code has proper structure and imports."""
        assistant = CensusAssistant()

        assistant.conversation.state.geography = "state"
        assistant.conversation.state.variables = ["B19013_001E"]
        assistant.conversation.state.year = 2020

        code = assistant._generate_pytidycensus_code()

        # Check code structure
        lines = code.strip().split("\n")

        # Should start with import
        assert lines[0] == "import pytidycensus as tc"

        # Should have API key setup
        assert any("census_api_key" in line for line in lines)

        # Should have main function call
        assert any("tc.get_acs(" in line for line in lines)

        # Should have print statements
        assert any("print(" in line for line in lines)

        # Should be valid Python syntax
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}\nCode:\n{code}")


def run_verbose_tests():
    """Run tests with verbose output showing conversation state and generated code."""
    test = TestConversationIntegration()

    print("🧪 Running Integration Tests with Verbose Output")
    print("=" * 80)

    try:
        print("\n" + "=" * 50)
        print("TEST 1: Basic ACS Query Generation")
        print("=" * 50)
        test.test_query_generation_from_state()
        print("✅ Basic query generation works!")

        print("\n" + "=" * 50)
        print("TEST 2: DC Inequality Analysis")
        print("=" * 50)
        test.test_dc_query_generation()
        print("✅ DC query generation works!")

        print("\n" + "=" * 50)
        print("TEST 3: 2020 Decennial Census")
        print("=" * 50)
        test.test_decennial_query_generation()
        print("✅ Decennial query generation works!")

        print("\n" + "=" * 50)
        print("TEST 4: Spatial Data with Geometry")
        print("=" * 50)
        test.test_geometry_query_generation()
        print("✅ Geometry query generation works!")

        print("\n" + "=" * 80)
        print("🎉 All integration tests passed with verbose output!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "verbose":
        # Run with verbose conversation state display
        run_verbose_tests()
    else:
        # Run basic tests without verbose output
        test = TestConversationIntegration()

        print("Testing query generation...")
        test.test_query_generation_from_state()
        print("✅ Basic query generation works!")

        test.test_dc_query_generation()
        print("✅ DC query generation works!")

        test.test_conversation_state_ready_check()
        print("✅ Conversation state validation works!")

        test.test_expected_query_patterns()
        print("✅ Query patterns match documentation!")

        print("\n🎉 All integration tests passed!")
        print("\nTo see verbose output with conversation state and generated code:")
        print("  python test_conversation_integration.py verbose")
