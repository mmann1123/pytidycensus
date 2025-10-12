====================
Census LLM Assistant
====================

The Census LLM Assistant provides a conversational interface to US Census data using Large Language Models. Instead of learning Census variable codes and geography hierarchies, you can describe your research needs in natural language.

The assistant is specifically trained on pytidycensus functionality and will only recommend pytidycensus functions, never other Census libraries. It includes comprehensive knowledge of common variable codes, geographic levels, and best practices.

Key Features
============

- **Conversational Interface**: Ask questions in natural language
- **Smart Variable Selection**: Automatically finds appropriate Census variables
- **Selective Normalization**: Only suggests denominators when needed (not for medians, rates, etc.)
- **Variable Name Cleaning**: Removes confusing 'E' suffixes (B19013_001E → B19013_001)
- **Geographic Guidance**: Helps choose the right geographic level for your research
- **Code Generation**: Produces ready-to-run pytidycensus code

Quick Start
===========

Command Line Interface (Recommended)
-------------------------------------

After installation, run the CLI with your API keys from your terminal:

.. code-block:: bash

   python -m pytidycensus.llm_interface.cli --census-key YOUR_CENSUS_KEY --openai-key YOUR_OPENAI_KEY

Then type your request, e.g.:

.. code-block:: text

   📊 You: Get median income by county in Texas

   🤔 Thinking...

   🏛️  Assistant: To analyze the median income by county in Texas, we will use the `get_acs()` function from pytidycensus to retrieve the necessary data. We will specifically request the median household income variable (`B19013_001E`) along with the total number of households (`B19001_001E`) to ensure proper normalization.

   Here's the code example to get the median income by county in Texas for the most recent available year:

.. code-block:: python

   import pytidycensus as tc

   # Get the median household income and total households for Texas counties
   income_data = tc.get_acs(
       geography="county",
       variables=[
           "B19013_001E",  # Median household income
           "B19001_001E",  # Total households (normalization variable)
       ],
       state="TX",  # Specify the state as Texas
       year=2020,  # Choose the desired year (most recent available)
       output="wide"  # Spread variables across columns for better readability
   )

   # Calculate any derived metrics if needed, such as income per household
   income_data['income_per_household'] = income_data['B19013_001E'] / income_data['B19001_001E']

   # Display the resulting DataFrame with median income and additional metrics
   print(income_data)

In this code:

- We request the median household income (``B19013_001E``) and total households (``B19001_001E``) for all counties in Texas in the year 2020.
- The ``output="wide"`` parameter is used to spread the variables across columns in the resulting DataFrame.
- We calculate the income per household by dividing the median household income by the total number of households.

This code will provide you with a DataFrame containing the median income by county in Texas along with any additional derived metrics you choose to calculate. Feel free to adjust the year or add more variables as needed for further analysis.

In Jupyter Notebook
-------------------

.. code-block:: python

   from pytidycensus.llm_interface import CensusAssistant

   # Initialize assistant
   assistant = CensusAssistant(
       census_api_key="your_census_api_key",
       openai_api_key="your_openai_key"  # Optional
   )

   # Ask for data (use await directly in Jupyter)
   response = await assistant.chat("Get median income by county in Texas")
   print(response)

**What you'll see:**

.. code-block:: text

   🏛️ Assistant: I'll help you get median income data for Texas counties.

   I found the right variable:
   • B19013_001E: Median household income

   Here's your pytidycensus code:

.. code-block:: python

   import pytidycensus as tc

   data = tc.get_acs(
       geography="county",
       variables=["B19013_001E"],
       state="TX",
       year=2020,
       output="wide",
       api_key=census_api_key
   )

Your data is ready! The column ``B19013_001`` contains median income for each Texas county.

The assistant automatically:

- ✅ Finds the right Census variable (``B19013_001E``)
- ✅ Uses wide format output for easy analysis
- ✅ Cleans column names (``B19013_001E`` → ``B19013_001``)
- ✅ Generates ready-to-run code

Try It Right Now (No Setup Required)
-------------------------------------

If you just want to see how it works without any API keys:

.. code-block:: bash

   # Test the conversation examples
   python tests/test_conversation_to_query.py verbose

   # Or see the normalization intelligence demo
   python examples/llm_assistant_example.py

These will show you exactly what conversations look like and which variables get normalization suggestions.

Installation
============

Basic Installation
------------------

.. code-block:: bash

   pip install pytidycensus[LLM]

LLM Dependencies
----------------

To use the LLM assistant, you need either OpenAI or a local model like Ollama. In order to get an API key for OpenAI, `sign up here <https://platform.openai.com/signup>`_ or `watch this video <https://youtu.be/dJ5aIRUyhNA?si=KXKoFYkQk4rpsUcx>`_.

The LLM cannot work without one of these configured:

**Option A: OpenAI (Recommended for reliability)**

.. code-block:: bash

   pip install openai
   export OPENAI_API_KEY="your_key_here"

**Option B: Local Models (Free, requires setup)**

.. code-block:: bash

   pip install ollama
   # Install Ollama from https://ollama.ai/
   ollama pull llama3.2
   ollama serve

Census API Key
--------------

Get a free Census API key and set it as an environment variable from your terminal:

.. code-block:: bash

   # Get key at: https://api.census.gov/data/key_signup.html
   export CENSUS_API_KEY="your_census_key_here"

Or use python to set it directly:

.. code-block:: python

   import os
   os.environ["CENSUS_API_KEY"] = "your_census_key_here"


Command Line Interface
======================

For interactive exploration:

.. code-block:: bash

   # Start interactive session
   python -m pytidycensus.llm_interface.cli

   # With API keys if not set in environment
   python -m pytidycensus.llm_interface.cli --census-key YOUR_KEY --openai-key YOUR_KEY

Commands in CLI
---------------

- ``help``: Show help information
- ``reset``: Start new conversation
- ``state``: Show current conversation state
- ``export``: Save conversation to JSON
- ``quit``: Exit



Configuration Options
=====================

LLM Provider Priority
---------------------

The assistant tries providers in order:

1. **OpenAI GPT-3.5 Turbo** (reliable, ~$0.01 per conversation)
2. **Local Ollama** (free, requires local setup)

Custom Configuration
--------------------

.. code-block:: python

   from pytidycensus.llm_interface import LLMManager, OpenAIProvider, OllamaProvider

   # Create custom provider setup
   providers = [
       OpenAIProvider(model="gpt-4", api_key="your_key"),
       OllamaProvider(model="mixtral:8x7b")  # Larger local model
   ]

   llm_manager = LLMManager(providers)
   assistant = CensusAssistant(llm_manager=llm_manager)

Real Example Conversations
===========================

These examples are taken directly from our test suite and demonstrate actual conversation flows:

Example 1: Wisconsin County Income Analysis
--------------------------------------------

.. code-block:: text

   👤 User: I'm studying household income variations in Wisconsin
   🏛️ Assistant: Great! I can help with income data. What geographic level do you need?

   👤 User: I want county-level data
   🏛️ Assistant: Perfect. County-level analysis provides good detail. What state are you interested in?

   👤 User: Use the most recent data available
   🏛️ Assistant: 2020 ACS data is a good choice. Should I use the 5-year estimates for better coverage?

   👤 User: Generate the pytidycensus code
   🏛️ Assistant: I'll generate the pytidycensus code for you now.

   📋 Final State: geography=county, variables=['B19013_001'], state=WI, year=2020, dataset=acs5

**Generated Code:**

.. code-block:: python

   import pytidycensus as tc

   # Set your Census API key
   # Get one at: https://api.census.gov/data/key_signup.html
   census_api_key = "YOUR_API_KEY_HERE"

   # Get Census data (wide format with cleaned variable names)
   data = tc.get_acs(
       geography="county",
       variables=["B19013_001E"],
       state="WI",
       year=2020,
       output="wide",
       api_key=census_api_key
   )

   # Clean variable names by removing 'E' suffix
   column_mapping = {col: col[:-1] for col in data.columns
                     if col.endswith('E') and '_' in col and col.split('_')[0].startswith('B')}
   if column_mapping:
       data = data.rename(columns=column_mapping)
       print(f"Cleaned {len(column_mapping)} variable names by removing 'E' suffix")

   print(f"Retrieved {data.shape[0]} rows and {data.shape[1]} columns")
   print(data.head())

**Result:** DataFrame with Wisconsin county data where ``B19013_001E`` becomes ``B19013_001``

Example 2: DC Inequality Analysis with Normalization
-----------------------------------------------------

.. code-block:: text

   👤 User: I want to study inequality in Washington DC
   🏛️ Assistant: I understand. What additional details do you need for this analysis?

   👤 User: Get poverty and income data by Census tract
   🏛️ Assistant: Census tracts are ideal for neighborhood-level analysis. Which state and county?

   👤 User: Include both counts and totals for calculating rates
   🏛️ Assistant: I understand. What additional details do you need for this analysis?

   👤 User: Use 2020 ACS 5-year data
   🏛️ Assistant: 2020 ACS data is a good choice. Should I use the 5-year estimates for better coverage?

   👤 User: Yes, generate the code
   🏛️ Assistant: I'll generate the pytidycensus code for you now.

   📋 Final State: geography=tract, variables=['B17001_002E', 'B17001_001E', 'B19013_001E'], state=DC, year=2020

**Generated Code:**

.. code-block:: python

   import pytidycensus as tc

   # Set your Census API key
   census_api_key = "YOUR_API_KEY_HERE"

   # Get Census data (wide format with cleaned variable names)
   data = tc.get_acs(
       geography="tract",
       variables=["B17001_002E", "B17001_001E", "B19013_001E"],
       state="DC",
       year=2020,
       output="wide",
       api_key=census_api_key
   )

   # Clean variable names by removing 'E' suffix
   column_mapping = {col: col[:-1] for col in data.columns
                     if col.endswith('E') and '_' in col and col.split('_')[0].startswith('B')}
   if column_mapping:
       data = data.rename(columns=column_mapping)

   print(f"Retrieved {data.shape[0]} rows and {data.shape[1]} columns")
   print(data.head())

   # Calculate poverty rate
   data['poverty_rate'] = (data['B17001_002'] / data['B17001_001']) * 100

**Result:**

- ``B17001_002E`` (poverty count) → ``B17001_002``
- ``B17001_001E`` (total for poverty) → ``B17001_001``
- ``B19013_001E`` (median income) → ``B19013_001``

Notice how the assistant automatically included the normalization variable (``B17001_001E``) for calculating poverty rates, but did NOT suggest a denominator for median income since it's already a rate.

Example 3: Spatial Analysis with Geometry
------------------------------------------

.. code-block:: text

   👤 User: I need Wisconsin county income data for mapping
   🏛️ Assistant: I understand. What additional details do you need for this analysis?

   👤 User: Include geographic boundaries
   🏛️ Assistant: I understand. What additional details do you need for this analysis?

   👤 User: 2020 ACS data
   🏛️ Assistant: 2020 ACS data is a good choice. Should I use the 5-year estimates for better coverage?

   👤 User: Generate the mapping-ready code
   🏛️ Assistant: I'll generate the pytidycensus code for you now.

   📋 Final State: geography=county, variables=['B19013_001'], state=WI, year=2020, geometry=True

**Generated Code:**

.. code-block:: python

   import pytidycensus as tc

   # Get Census data (wide format with cleaned variable names)
   data = tc.get_acs(
       geography="county",
       variables=["B19013_001E"],
       state="WI",
       year=2020,
       output="wide",
       geometry=True,
       api_key=census_api_key
   )

   print(f"Retrieved {data.shape[0]} rows and {data.shape[1]} columns")
   print(data.head())

   # Ready for mapping with GeoPandas
   data.plot(column='B19013_001', legend=True)

**Result:** GeoPandas GeoDataFrame ready for mapping with clean column name ``B19013_001``

Example 4: Direct Population Query
-----------------------------------

.. code-block:: text

   👤 User: Get me total population by state for 2020 decennial census
   🏛️ Assistant: ✅ Success! I retrieved your Census data:

   **Results**: 51 rows × 4 columns
   **Data preview:**
         GEOID        NAME  P1_001
   0        01     Alabama 5024279
   1        02      Alaska  733391
   2        04     Arizona 7151502
   3        05    Arkansas 3011524
   4        06  California39538223

   **Generated code:**

.. code-block:: python

   import pytidycensus as tc

   # Get Census data (wide format with cleaned variable names)
   data = tc.get_decennial(
       geography="state",
       variables=["P1_001N"],
       year=2020,
       output="wide",
       api_key=census_api_key
   )

   # Clean variable names by removing 'E' suffix
   # (Note: Decennial variables use 'N' suffix, so no cleaning needed)
   print(f"Retrieved {data.shape[0]} rows and {data.shape[1]} columns")
   print(data.head())

Selective Normalization in Action
----------------------------------

The assistant now intelligently determines when normalization variables are needed:

**✅ Variables that GET normalization suggestions:**

- ``B08301_021E`` (Workers who walked) → Suggests ``B08301_001E`` (Total workers)
- ``B25003_002E`` (Owner occupied units) → Suggests ``B25003_001E`` (Total occupied units)
- ``B19001_017E`` (Households with income $200k+) → Suggests ``B19001_001E`` (Total households)

**❌ Variables that do NOT get normalization suggestions:**

- ``B19013_001E`` (Median household income) - Already a median
- ``B25064_001E`` (Median gross rent) - Already a median
- ``B08006_008E`` (Mean travel time) - Already a mean
- ``B25119_001E`` (Housing cost as percentage) - Already a rate
- Any variable ending in ``_001E`` - These ARE the totals

This prevents the confusion of suggesting denominators for variables that don't need them.

Testing and Development
=======================

Run Test Conversations
-----------------------

See actual conversation flows and generated code:

.. code-block:: bash

   # Run verbose conversation tests
   python tests/test_conversation_to_query.py verbose

   # Run specific test
   python tests/test_conversation_to_query.py verbose wisconsin
   python tests/test_conversation_to_query.py verbose dc

Troubleshooting
===============

Common Issues
-------------

**No LLM providers available:**

.. code-block:: bash

   pip install openai  # For OpenAI
   # OR
   pip install ollama && ollama serve  # For local models

**Census API key issues:**

.. code-block:: bash

   export CENSUS_API_KEY="your_key_here"
   # Get free key: https://api.census.gov/data/key_signup.html

**Variable not found errors:**

- The assistant uses knowledge base + search to find variables
- Some very specific variables may need manual specification
- Use ``search_variables()`` function for exploration

Contributing
============

The LLM interface is designed to be extensible:

- Add new variable mappings in ``knowledge_base.py``
- Extend geography guidance with local expertise
- Contribute test cases for new conversation patterns
- Help improve normalization logic for edge cases

The goal is making Census data accessible through natural conversation!
