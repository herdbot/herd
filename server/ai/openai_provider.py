"""OpenAI provider implementation for herdbot."""

import json
from typing import Any

import structlog

from .base import AIProvider

logger = structlog.get_logger()

# Default system prompts
INTERPRET_SYSTEM_PROMPT = """You are an AI assistant for a robotics system called Herdbot.
Your role is to interpret sensor data and device states.
Provide clear, concise interpretations that help operators understand what's happening.
Focus on actionable insights and potential issues."""

PLAN_SYSTEM_PROMPT = """You are an AI planner for a robotics system called Herdbot.
Your role is to break down high-level goals into executable action steps.
Each step should be a specific command that can be sent to a device.
Consider constraints, safety, and efficiency in your plans.

Output format: Return a JSON array of steps, each with:
- action: The command action name
- device_id: Target device (or "all" for broadcast)
- params: Command parameters as an object
- description: Human-readable description"""

CHAT_SYSTEM_PROMPT = """You are an AI assistant for a robotics system called Herdbot.
Help users understand and control their robotic devices.
You can answer questions about the system, suggest commands, and troubleshoot issues.
Be helpful, concise, and safety-conscious."""


class OpenAIProvider(AIProvider):
    """OpenAI/GPT provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use
            temperature: Sampling temperature
        """
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    async def interpret(self, data: dict[str, Any], prompt: str) -> dict[str, Any]:
        """Interpret data using GPT."""
        client = self._get_client()

        messages = [
            {"role": "system", "content": INTERPRET_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"{prompt}\n\nData:\n```json\n{json.dumps(data, indent=2)}\n```",
            },
        ]

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
            )

            return {
                "interpretation": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else None,
            }

        except Exception as e:
            logger.error("openai_interpret_error", error=str(e))
            raise

    async def plan(
        self,
        goal: str,
        context: dict[str, Any],
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate action plan using GPT."""
        client = self._get_client()

        constraint_text = ""
        if constraints:
            constraint_text = "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)

        messages = [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Goal: {goal}\n\nContext:\n```json\n{json.dumps(context, indent=2)}\n```{constraint_text}",
            },
        ]

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,  # Lower temperature for planning
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # Handle both {"steps": [...]} and direct array formats
            steps = result.get("steps", result) if isinstance(result, dict) else result

            return {
                "steps": steps,
                "tokens_used": response.usage.total_tokens if response.usage else None,
            }

        except Exception as e:
            logger.error("openai_plan_error", error=str(e))
            raise

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Chat with GPT."""
        client = self._get_client()

        messages = [
            {"role": "system", "content": system_prompt or CHAT_SYSTEM_PROMPT}
        ]

        # Add history
        if history:
            for msg in history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            response = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
            )

            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else None,
            }

        except Exception as e:
            logger.error("openai_chat_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check OpenAI API availability."""
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False
