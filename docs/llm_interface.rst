LLM Interface
=============

pytidycensus includes an optional LLM (Large Language Model) interface that allows you to query Census data using natural language. This interface leverages OpenAI's language models to translate your questions into the appropriate Census API calls.

Installation
------------

To use the LLM interface, you need to install pytidycensus with the LLM extra dependencies:

.. code-block:: bash

   pip install pytidycensus[llm]

This will install the additional dependencies required for the LLM interface.

Installation Options
~~~~~~~~~~~~~~~~~~~~

**Option 1: OpenAI (Reliable, ~$0.01/conversation)**

.. code-block:: bash

   pip install openai
   export OPENAI_API_KEY="your_key"

**Option 2: Local Ollama (Free, requires setup)**

.. code-block:: bash

   pip install ollama
   # Install from https://ollama.ai/
   ollama pull llama3.2
   ollama serve

**Census API Key (Required for data)**

.. code-block:: bash

   # Get free key: https://api.census.gov/data/key_signup.html
   export CENSUS_API_KEY="your_census_key"

OpenAI API Key Setup
--------------------

To use the LLM interface, you'll need an OpenAI API key. Here's how to get one:

1. **Get an OpenAI API Key**: Visit the `OpenAI API website <https://platform.openai.com/api-keys>`_ to create an account and generate an API key.

2. **Video Tutorial**: For a step-by-step guide on getting your OpenAI API key, watch this helpful video: `How to Get OpenAI API Key <https://youtu.be/dJ5aIRUyhNA?si=0PtJSDX1yVxwCWF3>`_

3. **Set Your API Key**: Once you have your key, set it as an environment variable:

.. code-block:: bash

   export OPENAI_API_KEY="your_openai_api_key_here"

Or set it in your Python code:

.. code-block:: python

   import os
   os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"

**Jupyter Notebook Users**: If you're using Jupyter notebooks, environment variables may not be available. Use the helper function instead:

.. code-block:: python

   import pytidycensus as tc
   
   # Set both API keys at once
   tc.set_llm_api_keys(
       openai_api_key="your_openai_api_key_here",
       census_api_key="your_census_api_key_here"  # optional if already set
   )

Basic Usage
-----------

The LLM interface is accessed through the command line interface. Once you have the LLM interface installed and your API keys configured, you can start an interactive session:

.. code-block:: bash

   python -m pytidycensus.llm_interface.cli

This will start an interactive conversation where you can ask natural language questions about Census data:

.. code-block:: text

    🏛️  Welcome to Census Assistant! 🏛️

    I'll help you find and retrieve US Census data using natural language.
    Just tell me what you're researching!

    Examples:
    - "I'm studying income inequality in California"
    - "I need population data by race for Chicago"
    - "Show me median rent in urban areas"

   📊 You: What is the median household income in California counties?

    🤔 Thinking...
    Loaded cached variables for 2020 acs acs5
    
    🏛️  Assistant: For exploring the median household income in California counties, the most relevant variable to use is:

    - **Median Household Income**: `B19013_001E`

    To ensure proper normalization when calculating rates or percentages, you should include the following total variable:

    - **Total Households**: `B19001_001E`

    Here's how you can structure your query to get the median household income in California counties using pytidycensus:

    1. Retrieve the median household income (`B19013_001E`) and the total households (`B19001_001E`) for California counties.
    2. Calculate the rate or percentage of interest by dividing the median household income by the total households.

    Here's an example of how you can do this:

    ```python
    import pytidycensus as tc

    # Get the median household income and total households for California counties
    income_data = tc.get_acs(
        geography="county",
        variables=[
            "B19013_001E",  # Median Household Income
            "B19001_001E"   # Total Households (denominator)
        ],
        state="CA",
        year=2020,
        survey="acs5"
    )

    # Calculate the percentage of median household income to total households
    income_data['median_income_percentage'] = (income_data['B19013_001E'] / income_data['B19001_001E']) * 100

    print(income_data.head())
    ```

    This code will fetch the median household income and total households data for California counties in 2020 using the ACS 5-year estimates. It then calculates the percentage of median household income to total households, providing you with a normalized view of the data.      

The LLM interface will:

1. Interpret your natural language question
2. Identify the appropriate Census variables and geographic level
3. Guide you through the data collection process
4. Generate working pytidycensus code to retrieve your data
5. Provide conversational guidance throughout the process

Advanced Usage
--------------

**Command Line Interface**

You can ask more specific queries through the interactive command line interface:

.. code-block:: bash

   python -m pytidycensus.llm_interface.cli

Example conversation:

.. code-block:: text

   > Show me poverty rates by census tract in Harris County, Texas
   > Get population density by county in New York state with geometry
   > Compare median age between 2010 and 2020 for all states

**Direct CensusAssistant Interface**

For more control and conversational interactions, use the CensusAssistant class directly:

.. code-block:: python

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

**Programmatic Interface**

You can also use the CensusAssistant programmatically in your own scripts for custom workflows.

Features
--------

The LLM interface provides powerful capabilities:

- **Natural Language**: Describe research needs in plain English
- **Variable Discovery**: Finds relevant Census variables automatically
- **Geography Guidance**: Helps choose appropriate geographic levels
- **Code Generation**: Produces working pytidycensus code
- **Data Execution**: Can run queries and return results
- **Cost Effective**: Uses cheap models with local fallback
- **Multi-year Comparisons**: Retrieving data across different time periods
- **Spatial Data**: Including geometry when needed for mapping

Tips for Better Results
-----------------------

To get the best results from the LLM interface:

1. **Be Specific**: Include geographic areas, time periods, and specific metrics when possible
2. **Use Standard Terms**: Reference common demographic concepts (income, population, age, etc.)
3. **Specify Output Format**: Mention if you need geometry for mapping
4. **Ask Follow-up Questions**: The interface can handle related queries building on previous requests

Example Queries
---------------

Here are some example natural language queries you can try:

.. code-block:: python

   # Demographic queries
   tc.ask("What is the racial composition of Chicago?")
   tc.ask("Show me educational attainment in rural counties")
   
   # Economic queries  
   tc.ask("Which states have the highest unemployment rates?")
   tc.ask("Get median home values by metropolitan area")
   
   # Spatial queries
   tc.ask("Give me population density by census tract in Los Angeles County with geometry")
   tc.ask("Show me the counties with the fastest population growth")

Example Conversations
---------------------

The LLM interface can handle complex research workflows through conversation:

**Housing Affordability Research**

.. code-block:: text

   User: "I'm studying housing affordability in major cities"
   
   Assistant: Suggests median rent and income variables
            → Recommends place-level geography for cities
            → Generates code to retrieve and analyze data

**Variable Discovery**

.. code-block:: text

   User: "What poverty data is available?"
   
   Assistant: Searches Census variable catalog
            → Explains different poverty measures  
            → Shows specific variable codes and descriptions

Limitations
-----------

Keep in mind that the LLM interface:

- Requires an active internet connection and valid API key (OpenAI or local Ollama setup)
- OpenAI usage has associated costs (~$0.01/conversation), though Ollama provides free local alternative
- Works best with standard demographic and economic queries
- May need clarification for very complex or ambiguous requests
- Local Ollama setup requires more initial configuration but provides unlimited free usage

Troubleshooting
---------------

**"OpenAI API key is required" Error**

If you get this error even though you've set the ``OPENAI_API_KEY`` environment variable:

1. **In Jupyter Notebooks**: Environment variables may not be available. Use the helper function:

   .. code-block:: python

      import pytidycensus as tc
      tc.set_llm_api_keys(openai_api_key="your_key_here")

2. **Restart your kernel/session**: After setting environment variables, restart your Python kernel or terminal session

3. **Use direct parameters**: Pass the API key directly to the function:

   .. code-block:: python

      result = tc.ask("your question", openai_api_key="your_key_here")

**Other Common Issues**

- **Missing dependencies**: Install with ``pip install pytidycensus[llm]``
- **Census API key not set**: Use ``tc.set_census_api_key("your_key")`` first
- **Network connectivity**: Ensure you have internet access for API calls
- **Local Ollama setup**: If using Ollama, ensure the service is running with ``ollama serve``
- **Model availability**: For Ollama, make sure you've pulled the required model: ``ollama pull llama3.2``

Getting Help
------------

For technical support and bug reports, please visit our `GitHub repository <https://github.com/mmann1123/pytidycensus>`_.