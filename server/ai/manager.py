"""AI provider manager for herdbot.

Routes AI requests to appropriate providers and manages API keys.
"""

from typing import Any

import structlog

from server.core import get_settings

from .base import AIProvider

logger = structlog.get_logger()

# Global manager instance
_manager: "AIManager | None" = None


class AIManager:
    """Manages AI providers and routes requests.

    Supports multiple providers (OpenAI, Anthropic) with automatic
    fallback and load balancing.
    """

    def __init__(self) -> None:
        """Initialize the AI manager."""
        self._providers: dict[str, AIProvider] = {}
        self._default_provider: str | None = None
        self._initialized = False

    def _initialize(self) -> None:
        """Lazy initialization of providers based on settings."""
        if self._initialized:
            return

        settings = get_settings()

        # Initialize OpenAI if configured
        if settings.openai_api_key:
            try:
                from .openai_provider import OpenAIProvider
                self._providers["openai"] = OpenAIProvider(
                    api_key=settings.openai_api_key,
                )
                logger.info("openai_provider_initialized")
            except ImportError:
                logger.warning("openai_package_not_installed")

        # Initialize Anthropic if configured
        if settings.anthropic_api_key:
            try:
                from .anthropic_provider import AnthropicProvider
                self._providers["anthropic"] = AnthropicProvider(
                    api_key=settings.anthropic_api_key,
                )
                logger.info("anthropic_provider_initialized")
            except ImportError:
                logger.warning("anthropic_package_not_installed")

        # Set default provider
        if settings.default_ai_provider in self._providers:
            self._default_provider = settings.default_ai_provider
        elif self._providers:
            self._default_provider = next(iter(self._providers))

        self._initialized = True

    def _get_provider(self, provider_name: str | None = None) -> AIProvider:
        """Get a provider by name or return default."""
        self._initialize()

        if not self._providers:
            raise RuntimeError("No AI providers configured")

        name = provider_name or self._default_provider
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")

        return self._providers[name]

    async def interpret(
        self,
        data: dict[str, Any],
        prompt: str,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Interpret data using AI.

        Args:
            data: Data to interpret
            prompt: Interpretation instructions
            provider: Optional specific provider

        Returns:
            Interpretation result with provider info
        """
        ai = self._get_provider(provider)

        result = await ai.interpret(data, prompt)
        result["provider"] = ai.name
        result["model"] = ai.model

        return result

    async def plan(
        self,
        goal: str,
        context: dict[str, Any],
        constraints: list[str] | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Generate action plan.

        Args:
            goal: Goal to achieve
            context: Current context
            constraints: Optional constraints
            provider: Optional specific provider

        Returns:
            Plan with provider info
        """
        ai = self._get_provider(provider)

        result = await ai.plan(goal, context, constraints)
        result["provider"] = ai.name
        result["model"] = ai.model

        return result

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Chat with AI.

        Args:
            message: User message
            history: Conversation history
            system_prompt: Optional system prompt
            provider: Optional specific provider

        Returns:
            Response with provider info
        """
        ai = self._get_provider(provider)

        result = await ai.chat(message, history, system_prompt)
        result["provider"] = ai.name
        result["model"] = ai.model

        return result

    def list_providers(self) -> list[str]:
        """List available provider names."""
        self._initialize()
        return list(self._providers.keys())

    @property
    def default_provider(self) -> str | None:
        """Get default provider name."""
        self._initialize()
        return self._default_provider


def get_ai_manager() -> AIManager:
    """Get the global AI manager instance."""
    global _manager
    if _manager is None:
        _manager = AIManager()
    return _manager
