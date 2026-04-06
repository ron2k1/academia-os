"""Tests for the intent router."""
from __future__ import annotations

from src.orchestrator.router import AgentType, route_intent


class TestAgentType:
    """Tests for the AgentType enum."""

    def test_all_agent_types_exist(self) -> None:
        """All expected agent types are defined."""
        assert AgentType.TUTOR.value == "tutor"
        assert AgentType.QUESTION_CREATOR.value == "question_creator"
        assert AgentType.NOTE_SUMMARIZER.value == "note_summarizer"
        assert AgentType.TEST_CREATOR.value == "test_creator"
        assert AgentType.HOMEWORK_FINISHER.value == "homework_finisher"


class TestRouteIntent:
    """Tests for the route_intent function."""

    def test_routes_to_test_creator(self) -> None:
        """Routes messages with test-related keywords."""
        assert route_intent("Create a practice test") == AgentType.TEST_CREATOR
        assert route_intent("Make a mock exam") == AgentType.TEST_CREATOR
        assert route_intent("Generate exam for me") == AgentType.TEST_CREATOR

    def test_routes_to_question_creator(self) -> None:
        """Routes messages with question-related keywords."""
        assert route_intent("Generate question on calc") == AgentType.QUESTION_CREATOR
        assert route_intent("Quiz me on physics") == AgentType.QUESTION_CREATOR
        assert route_intent("Make a flashcard set") == AgentType.QUESTION_CREATOR

    def test_routes_to_homework_finisher(self) -> None:
        """Routes messages with homework-related keywords."""
        assert route_intent("Help with my homework") == AgentType.HOMEWORK_FINISHER
        assert route_intent("Finish my assignment") == AgentType.HOMEWORK_FINISHER
        assert route_intent("Problem set 3 help") == AgentType.HOMEWORK_FINISHER

    def test_routes_to_note_summarizer(self) -> None:
        """Routes messages with summary-related keywords."""
        assert route_intent("Summarize these notes") == AgentType.NOTE_SUMMARIZER
        assert route_intent("Give me key points") == AgentType.NOTE_SUMMARIZER
        assert route_intent("TLDR of lecture") == AgentType.NOTE_SUMMARIZER

    def test_routes_to_tutor(self) -> None:
        """Routes messages with tutor-related keywords."""
        assert route_intent("Explain integration") == AgentType.TUTOR
        assert route_intent("Help me understand limits") == AgentType.TUTOR
        assert route_intent("Teach me about matrices") == AgentType.TUTOR

    def test_defaults_to_tutor(self) -> None:
        """Unmatched messages default to TUTOR."""
        assert route_intent("Hello there") == AgentType.TUTOR
        assert route_intent("Random unrelated text") == AgentType.TUTOR
        assert route_intent("") == AgentType.TUTOR

    def test_case_insensitive(self) -> None:
        """Keyword matching is case-insensitive."""
        assert route_intent("SUMMARIZE my notes") == AgentType.NOTE_SUMMARIZER
        assert route_intent("PRACTICE TEST please") == AgentType.TEST_CREATOR

    def test_priority_test_over_question(self) -> None:
        """Test creator keywords take priority over question creator."""
        # "practice test" should match test_creator, not question_creator
        result = route_intent("I want a practice test with questions")
        assert result == AgentType.TEST_CREATOR
