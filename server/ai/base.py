"""Base AI provider interface for herdbot.

Defines the abstract interface that all AI providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Abstract base class for AI providers.

    All AI integrations (OpenAI, Anthropic, etc.) must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Current model being used."""
        pass

    @abstractmethod
    async def interpret(self, data: dict[str, Any], prompt: str) -> dict[str, Any]:
        """Interpret sensor data or situation.

        Args:
            data: Data to interpret (sensor readings, device state, etc.)
            prompt: Instructions for interpretation

        Returns:
            Dictionary with:
                - interpretation: The AI's interpretation
                - confidence: Optional confidence score
                - details: Optional additional details
        """
        pass

    @abstractmethod
    async def plan(
        self,
        goal: str,
        context: dict[str, Any],
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate an action plan from a high-level goal.

        Args:
            goal: High-level goal to achieve
            context: Current system state and context
            constraints: Optional constraints on the plan

        Returns:
            Dictionary with:
                - steps: List of action steps
                - confidence: Optional confidence score
                - reasoning: Optional explanation
        """
        pass

    @abstractmethod
    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Conversational interface.

        Args:
            message: User message
            history: Conversation history (list of {"role": "user/assistant", "content": "..."})
            system_prompt: Optional system prompt override

        Returns:
            Dictionary with:
                - response: The AI's response
                - tokens_used: Optional token count
        """
        pass

    async def health_check(self) -> bool:
        """Check if the provider is available and working.

        Returns:
            True if provider is healthy
        """
        return True
