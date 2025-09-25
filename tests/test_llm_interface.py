"""Tests for LLM interface components.

Basic functionality tests that don't require API keys.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pytidycensus.llm_interface.conversation import ConversationManager, ConversationState
from pytidycensus.llm_interface.providers import LLMManager, LLMProvider


class TestConversationState:
    """Test conversation state management."""

    def test_conversation_state_creation(self):
        """Test basic state creation."""
        state = ConversationState()
        assert state.variables == []
        assert state.variable_descriptions == {}
        assert state.missing_info == []
        assert not state.is_ready_for_execution()

    def test_conversation_state_ready_check(self):
        """Test readiness checking."""
        state = ConversationState()
        assert not state.is_ready_for_execution()

        # Add required fields
        state.variables = ["B01001_001E"]
        state.geography = "state"
        assert state.is_ready_for_execution()

        # Geography requiring state
        state.geography = "county"
        assert not state.is_ready_for_execution()

        state.state = "CA"
        assert state.is_ready_for_execution()

    def test_get_missing_info(self):
        """Test missing info detection."""
        state = ConversationState()
        missing = state.get_missing_info()
        assert "variables" in missing
        assert "geography" in missing
        assert "year" in missing

    def test_state_serialization(self):
        """Test state to/from dict conversion."""
        state = ConversationState(
            research_question="Test research", variables=["B01001_001E"], geography="state"
        )

        state_dict = state.to_dict()
        assert state_dict["research_question"] == "Test research"
        assert state_dict["variables"] == ["B01001_001E"]
        assert state_dict["geography"] == "state"


class TestConversationManager:
    """Test conversation management."""

    def test_conversation_creation(self):
        """Test basic conversation creation."""
        conv = ConversationManager()
        assert isinstance(conv.state, ConversationState)
        assert conv.message_history == []

    def test_add_message(self):
        """Test adding messages to conversation."""
        conv = ConversationManager()
        conv.add_message("user", "Hello")
        conv.add_message("assistant", "Hi there!")

        assert len(conv.message_history) == 2
        assert conv.message_history[0]["role"] == "user"
        assert conv.message_history[0]["content"] == "Hello"

    def test_get_context_messages(self):
        """Test context message formatting."""
        conv = ConversationManager()
        conv.add_message("user", "Test message")

        messages = conv.get_context_messages()
        assert len(messages) >= 2  # System + user message
        assert messages[0]["role"] == "system"
        assert any(msg["role"] == "user" for msg in messages)

    def test_state_updates(self):
        """Test state updates."""
        conv = ConversationManager()
        conv.update_state({"research_question": "Test research", "geography": "state"})

        assert conv.state.research_question == "Test research"
        assert conv.state.geography == "state"

    def test_export_import_state(self):
        """Test state export and import."""
        conv = ConversationManager()
        conv.add_message("user", "Test")
        conv.update_state({"research_question": "Test research"})

        # Export
        exported = conv.export_state()
        assert isinstance(exported, str)
        data = json.loads(exported)
        assert "state" in data
        assert "message_history" in data

        # Import to new conversation
        conv2 = ConversationManager()
        conv2.import_state(exported)
        assert conv2.state.research_question == "Test research"
        assert len(conv2.message_history) == 1


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, model: str = "mock", available: bool = True):
        super().__init__(model)
        self.available = available

    async def chat_completion(self, messages, **kwargs):
        return "Mock response"

    async def structured_output(self, prompt, schema):
        return {"intent": "mock", "confidence": 0.8}

    def is_available(self):
        return self.available


class TestLLMManager:
    """Test LLM manager functionality."""

    def test_llm_manager_creation(self):
        """Test LLM manager creation."""
        providers = [MockLLMProvider("mock1"), MockLLMProvider("mock2")]
        manager = LLMManager(providers)
        assert len(manager.available_providers) == 2

    def test_unavailable_providers(self):
        """Test handling of unavailable providers."""
        providers = [MockLLMProvider("mock", available=False)]
        manager = LLMManager(providers)
        assert len(manager.available_providers) == 0

    @pytest.mark.asyncio
    async def test_chat_completion(self):
        """Test chat completion through manager."""
        provider = MockLLMProvider()
        manager = LLMManager([provider])

        response = await manager.chat_completion([{"role": "user", "content": "test"}])
        assert response == "Mock response"

    @pytest.mark.asyncio
    async def test_structured_output(self):
        """Test structured output through manager."""
        provider = MockLLMProvider()
        manager = LLMManager([provider])

        response = await manager.structured_output("test prompt", {})
        assert response["intent"] == "mock"

    @pytest.mark.asyncio
    async def test_provider_fallback(self):
        """Test fallback between providers."""
        # First provider fails, second succeeds
        provider1 = MockLLMProvider("fail")
        provider1.chat_completion = AsyncMock(side_effect=Exception("Failed"))

        provider2 = MockLLMProvider("success")
        manager = LLMManager([provider1, provider2])

        response = await manager.chat_completion([{"role": "user", "content": "test"}])
        assert response == "Mock response"


class TestProviderCreation:
    """Test provider creation functions."""

    @patch("pytidycensus.llm_interface.providers.OpenAIProvider")
    @patch("pytidycensus.llm_interface.providers.OllamaProvider")
    def test_create_default_llm_manager(self, mock_ollama, mock_openai):
        """Test default LLM manager creation."""
        # Mock providers as unavailable to avoid actual API calls
        mock_openai_instance = Mock()
        mock_openai_instance.is_available.return_value = False
        mock_openai.return_value = mock_openai_instance

        mock_ollama_instance = Mock()
        mock_ollama_instance.is_available.return_value = False
        mock_ollama.return_value = mock_ollama_instance

        from pytidycensus.llm_interface.providers import create_default_llm_manager

        manager = create_default_llm_manager()

        assert isinstance(manager, LLMManager)
        # Should create both providers even if unavailable
        assert mock_openai.called
        assert mock_ollama.called


@pytest.mark.integration
class TestIntegration:
    """Integration tests (require manual setup)."""

    def test_assistant_creation_no_keys(self):
        """Test assistant can be created without API keys."""
        from pytidycensus.llm_interface import CensusAssistant

        # Should not raise exception, just have no available providers
        assistant = CensusAssistant()
        assert assistant is not None
