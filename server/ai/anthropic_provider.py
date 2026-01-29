"""Anthropic/Claude provider implementation for herdbot."""

import json
from typing import Any

import structlog

from .base import AIProvider

logger = structlog.get_logger()

# System prompts
INTERPRET_SYSTEM_PROMPT = """You are an AI assistant for a robotics system called Herdbot.
Your role is to interpret sensor data and device states.
Provide clear, concise interpretations that help operators understand what's happening.
Focus on actionable insights and potential issues."""

PLAN_SYSTEM_PROMPT = """You are an AI planner for a robotics system called Herdbot.
Your role is to break down high-level goals into executable action steps.
Each step should be a specific command that can be sent to a device.
Consider constraints, safety, and efficiency in your plans.

Return your plan as a JSON object with a "steps" array. Each step should have:
- action: The command action name
- device_id: Target device (or "all" for broadcast)
- params: Command parameters as an object
- description: Human-readable description"""

CHAT_SYSTEM_PROMPT = """You are an AI assistant for a robotics system called Herdbot.
Help users understand and control their robotic devices.
You can answer questions about the system, suggest commands, and troubleshoot issues.
Be helpful, concise, and safety-conscious."""


class AnthropicProvider(AIProvider):
    """Anthropic/Claude provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 4096,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use
            max_tokens: Maximum tokens in response
        """
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    async def interpret(self, data: dict[str, Any], prompt: str) -> dict[str, Any]:
        """Interpret data using Claude."""
        client = self._get_client()

        try:
            response = await client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=INTERPRET_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nData:\n```json\n{json.dumps(data, indent=2)}\n```",
                    }
                ],
            )

            return {
                "interpretation": response.content[0].text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            }

        except Exception as e:
            logger.error("anthropic_interpret_error", error=str(e))
            raise

    async def plan(
        self,
        goal: str,
        context: dict[str, Any],
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate action plan using Claude."""
        client = self._get_client()

        constraint_text = ""
        if constraints:
            constraint_text = "\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)

        try:
            response = await client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=PLAN_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Goal: {goal}\n\nContext:\n```json\n{json.dumps(context, indent=2)}\n```{constraint_text}\n\nRespond with only the JSON object.",
                    }
                ],
            )

            content = response.content[0].text

            # Extract JSON from response
            # Handle case where Claude wraps in markdown code block
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            steps = result.get("steps", result) if isinstance(result, dict) else result

            return {
                "steps": steps,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            }

        except json.JSONDecodeError as e:
            logger.error("anthropic_plan_json_error", error=str(e), content=content[:200])
            raise ValueError(f"Failed to parse plan as JSON: {e}")
        except Exception as e:
            logger.error("anthropic_plan_error", error=str(e))
            raise

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Chat with Claude."""
        client = self._get_client()

        messages = []

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
            response = await client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt or CHAT_SYSTEM_PROMPT,
                messages=messages,
            )

            return {
                "response": response.content[0].text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            }

        except Exception as e:
            logger.error("anthropic_chat_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check Anthropic API availability."""
        try:
            client = self._get_client()
            # Simple check - try to create a minimal message
            await client.messages.create(
                model=self._model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False
