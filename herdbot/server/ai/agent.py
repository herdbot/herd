"""AI agent that autonomously monitors and responds to robot state.

Subscribes to topics and triggers AI when conditions are met.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog

from shared.schemas import Command, SensorReading

from .manager import get_ai_manager

logger = structlog.get_logger()


@dataclass
class Trigger:
    """Defines a condition that triggers AI processing.

    Attributes:
        name: Trigger identifier
        condition: Function that evaluates if trigger should fire
        prompt: AI prompt to use when triggered
        cooldown_s: Minimum seconds between triggers
        enabled: Whether trigger is active
    """

    name: str
    condition: Callable[[dict[str, Any]], bool]
    prompt: str
    cooldown_s: float = 5.0
    enabled: bool = True


class AIAgent:
    """AI agent that monitors robot state and responds autonomously.

    Subscribes to relevant topics and uses AI to:
    - Detect anomalies
    - Classify situations
    - Generate responses/commands
    """

    def __init__(self, provider: str | None = None) -> None:
        """Initialize the AI agent.

        Args:
            provider: Preferred AI provider
        """
        self._provider = provider
        self._triggers: dict[str, Trigger] = {}
        self._last_trigger_times: dict[str, datetime] = {}
        self._running = False
        self._recent_readings: dict[str, list[SensorReading]] = {}
        self._max_history = 100

        # Response callbacks
        self._on_detection: list[Callable[[str, dict[str, Any]], Any]] = []
        self._on_command: list[Callable[[Command], Any]] = []

    def add_trigger(self, trigger: Trigger) -> None:
        """Add a trigger condition.

        Args:
            trigger: Trigger to add
        """
        self._triggers[trigger.name] = trigger
        logger.info("trigger_added", name=trigger.name)

    def remove_trigger(self, name: str) -> bool:
        """Remove a trigger by name."""
        if name in self._triggers:
            del self._triggers[name]
            return True
        return False

    def on_detection(self, callback: Callable[[str, dict[str, Any]], Any]) -> None:
        """Register callback for AI detections."""
        self._on_detection.append(callback)

    def on_command(self, callback: Callable[[Command], Any]) -> None:
        """Register callback for generated commands."""
        self._on_command.append(callback)

    async def process_sensor_data(self, reading: SensorReading) -> None:
        """Process incoming sensor data.

        Args:
            reading: Sensor reading to process
        """
        device_id = reading.device_id

        # Store in history
        if device_id not in self._recent_readings:
            self._recent_readings[device_id] = []
        self._recent_readings[device_id].append(reading)

        # Trim history
        if len(self._recent_readings[device_id]) > self._max_history:
            self._recent_readings[device_id] = self._recent_readings[device_id][-self._max_history:]

        # Check triggers
        await self._check_triggers(reading)

    async def _check_triggers(self, reading: SensorReading) -> None:
        """Check all triggers against current data."""
        now = datetime.utcnow()

        # Build context for trigger evaluation
        context = {
            "reading": reading.model_dump(mode="json"),
            "device_id": reading.device_id,
            "sensor_type": reading.sensor_type,
            "value": reading.value,
            "history": [
                r.model_dump(mode="json")
                for r in self._recent_readings.get(reading.device_id, [])[-10:]
            ],
        }

        for name, trigger in self._triggers.items():
            if not trigger.enabled:
                continue

            # Check cooldown
            last_time = self._last_trigger_times.get(name)
            if last_time:
                elapsed = (now - last_time).total_seconds()
                if elapsed < trigger.cooldown_s:
                    continue

            # Evaluate condition
            try:
                if trigger.condition(context):
                    self._last_trigger_times[name] = now
                    await self._handle_trigger(trigger, context)
            except Exception as e:
                logger.error("trigger_evaluation_error", trigger=name, error=str(e))

    async def _handle_trigger(self, trigger: Trigger, context: dict[str, Any]) -> None:
        """Handle a triggered condition."""
        logger.info("trigger_fired", trigger=trigger.name)

        try:
            manager = get_ai_manager()

            # Get AI interpretation
            result = await manager.interpret(
                data=context,
                prompt=trigger.prompt,
                provider=self._provider,
            )

            detection = {
                "trigger": trigger.name,
                "interpretation": result["interpretation"],
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Notify callbacks
            for callback in self._on_detection:
                try:
                    coro = callback(trigger.name, detection)
                    if asyncio.iscoroutine(coro):
                        await coro
                except Exception as e:
                    logger.error("detection_callback_error", error=str(e))

        except Exception as e:
            logger.error("trigger_handling_error", trigger=trigger.name, error=str(e))

    async def generate_response(
        self,
        situation: str,
        context: dict[str, Any],
    ) -> list[Command]:
        """Generate commands in response to a situation.

        Args:
            situation: Description of the situation
            context: Current system context

        Returns:
            List of commands to execute
        """
        try:
            manager = get_ai_manager()

            # Get action plan
            result = await manager.plan(
                goal=f"Respond to: {situation}",
                context=context,
                provider=self._provider,
            )

            commands = []
            for step in result.get("steps", []):
                cmd = Command(
                    device_id=step.get("device_id", "unknown"),
                    action=step.get("action", "unknown"),
                    params=step.get("params", {}),
                )
                commands.append(cmd)

                # Notify callbacks
                for callback in self._on_command:
                    try:
                        coro = callback(cmd)
                        if asyncio.iscoroutine(coro):
                            await coro
                    except Exception as e:
                        logger.error("command_callback_error", error=str(e))

            return commands

        except Exception as e:
            logger.error("response_generation_error", error=str(e))
            return []


# Pre-built trigger conditions
def anomaly_trigger(threshold: float = 2.0) -> Trigger:
    """Create a trigger for anomalous sensor values.

    Args:
        threshold: Standard deviations from mean to trigger

    Returns:
        Configured trigger
    """
    def condition(ctx: dict[str, Any]) -> bool:
        history = ctx.get("history", [])
        if len(history) < 10:
            return False

        # Get current and historical values
        current = ctx.get("value")
        if not isinstance(current, (int, float)):
            return False

        values = []
        for h in history:
            v = h.get("value")
            if isinstance(v, (int, float)):
                values.append(v)

        if len(values) < 5:
            return False

        # Calculate mean and std
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5

        if std == 0:
            return False

        # Check if current value is anomalous
        z_score = abs(current - mean) / std
        return z_score > threshold

    return Trigger(
        name="anomaly_detection",
        condition=condition,
        prompt="Analyze this sensor reading that appears anomalous compared to recent history. Is this a real issue or sensor noise? What might be causing it?",
        cooldown_s=10.0,
    )


def threshold_trigger(
    name: str,
    sensor_type: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> Trigger:
    """Create a trigger for threshold violations.

    Args:
        name: Trigger name
        sensor_type: Sensor type to monitor
        min_value: Minimum acceptable value
        max_value: Maximum acceptable value

    Returns:
        Configured trigger
    """
    def condition(ctx: dict[str, Any]) -> bool:
        if ctx.get("sensor_type") != sensor_type:
            return False

        value = ctx.get("value")
        if not isinstance(value, (int, float)):
            return False

        if min_value is not None and value < min_value:
            return True
        if max_value is not None and value > max_value:
            return True

        return False

    return Trigger(
        name=name,
        condition=condition,
        prompt=f"A {sensor_type} sensor has exceeded its threshold limits. Analyze the situation and recommend appropriate action.",
        cooldown_s=5.0,
    )
