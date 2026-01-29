"""Zenoh messaging hub for herdbot.

Manages Zenoh session, topic subscriptions, and message routing.
"""

import asyncio
from collections.abc import Awaitable, Callable

import structlog
import zenoh
from zenoh import Config, Sample, Session, Subscriber

from shared.schemas import Command, CommandResponse, DeviceInfo, Heartbeat, SensorReading

from .config import Settings
from .device_registry import DeviceRegistry

logger = structlog.get_logger()

# Type alias for message handlers
MessageHandler = Callable[[str, bytes], Awaitable[None] | None]


class ZenohHub:
    """Central Zenoh messaging hub.

    Manages the Zenoh session, handles device discovery, and routes messages
    between devices and the server.
    """

    def __init__(self, settings: Settings, device_registry: DeviceRegistry) -> None:
        """Initialize the Zenoh hub.

        Args:
            settings: Application settings
            device_registry: Device registry instance
        """
        self._settings = settings
        self._registry = device_registry
        self._session: Session | None = None
        self._subscribers: list[Subscriber] = []
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._running = False

    async def start(self) -> None:
        """Start the Zenoh session and set up subscriptions."""
        if self._running:
            return

        logger.info(
            "zenoh_hub_starting",
            mode=self._settings.zenoh_mode,
            listen=self._settings.zenoh_listen,
        )

        # Configure Zenoh
        config = Config()

        # Set mode
        config.insert_json5("mode", f'"{self._settings.zenoh_mode}"')

        # Set listen endpoints
        if self._settings.zenoh_listen:
            endpoints = ", ".join(f'"{e}"' for e in self._settings.zenoh_listen)
            config.insert_json5("listen/endpoints", f"[{endpoints}]")

        # Set connect endpoints
        if self._settings.zenoh_connect:
            endpoints = ", ".join(f'"{e}"' for e in self._settings.zenoh_connect)
            config.insert_json5("connect/endpoints", f"[{endpoints}]")

        # Open session
        self._session = await zenoh.open(config)
        self._running = True

        # Set up core subscriptions
        await self._setup_subscriptions()

        logger.info("zenoh_hub_started", session_id=str(self._session.zid()))

    async def stop(self) -> None:
        """Stop the Zenoh session and clean up."""
        if not self._running:
            return

        self._running = False

        # Undeclare all subscribers
        for sub in self._subscribers:
            sub.undeclare()
        self._subscribers.clear()

        # Close session
        if self._session:
            self._session.close()
            self._session = None

        logger.info("zenoh_hub_stopped")

    async def _setup_subscriptions(self) -> None:
        """Set up core topic subscriptions."""
        if not self._session:
            return

        prefix = self._settings.topic_prefix

        # Device info subscription
        await self._subscribe(
            f"{prefix}/devices/*/info",
            self._handle_device_info,
        )

        # Heartbeat subscription
        await self._subscribe(
            f"{prefix}/devices/*/heartbeat",
            self._handle_heartbeat,
        )

        # Sensor data subscription
        await self._subscribe(
            f"{prefix}/sensors/**",
            self._handle_sensor_data,
        )

        # Command response subscription
        await self._subscribe(
            f"{prefix}/commands/*/response",
            self._handle_command_response,
        )

    async def _subscribe(self, topic: str, handler: MessageHandler) -> None:
        """Subscribe to a topic with a handler.

        Args:
            topic: Topic pattern to subscribe to
            handler: Async callback for messages
        """
        if not self._session:
            return

        def callback(sample: Sample) -> None:
            key = str(sample.key_expr)
            payload = bytes(sample.payload)
            asyncio.create_task(self._dispatch_message(key, payload, handler))

        sub = self._session.declare_subscriber(topic, callback)
        self._subscribers.append(sub)

        # Track handlers for external access
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

        logger.debug("subscribed", topic=topic)

    async def _dispatch_message(
        self, key: str, payload: bytes, handler: MessageHandler
    ) -> None:
        """Dispatch a message to its handler."""
        try:
            result = handler(key, payload)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error("message_handler_error", topic=key, error=str(e))

    async def _handle_device_info(self, key: str, payload: bytes) -> None:
        """Handle device info/registration messages."""
        try:
            device_info = DeviceInfo.from_msgpack(payload)
            await self._registry.register_device(device_info)
        except Exception as e:
            logger.error("device_info_parse_error", topic=key, error=str(e))

    async def _handle_heartbeat(self, key: str, payload: bytes) -> None:
        """Handle device heartbeat messages."""
        try:
            heartbeat = Heartbeat.from_msgpack(payload)
            await self._registry.update_heartbeat(
                device_id=heartbeat.device_id,
                uptime_ms=heartbeat.uptime_ms,
                load=heartbeat.load,
                memory_free=heartbeat.memory_free,
            )
        except Exception as e:
            logger.error("heartbeat_parse_error", topic=key, error=str(e))

    async def _handle_sensor_data(self, key: str, payload: bytes) -> None:
        """Handle sensor data messages."""
        try:
            reading = SensorReading.from_msgpack(payload)
            # Forward to registered handlers
            for handler in self._handlers.get("sensor_data", []):
                await self._dispatch_message(key, payload, handler)

            logger.debug(
                "sensor_data_received",
                device_id=reading.device_id,
                sensor_type=reading.sensor_type,
            )
        except Exception as e:
            logger.error("sensor_data_parse_error", topic=key, error=str(e))

    async def _handle_command_response(self, key: str, payload: bytes) -> None:
        """Handle command response messages."""
        try:
            response = CommandResponse.from_msgpack(payload)
            logger.debug(
                "command_response_received",
                request_id=str(response.request_id),
                success=response.success,
            )
        except Exception as e:
            logger.error("command_response_parse_error", topic=key, error=str(e))

    def add_sensor_handler(self, handler: MessageHandler) -> None:
        """Add a handler for sensor data messages."""
        if "sensor_data" not in self._handlers:
            self._handlers["sensor_data"] = []
        self._handlers["sensor_data"].append(handler)

    async def publish(self, topic: str, payload: bytes) -> None:
        """Publish a message to a topic.

        Args:
            topic: Topic to publish to
            payload: Message payload (MessagePack encoded)
        """
        if not self._session:
            raise RuntimeError("Zenoh session not started")

        self._session.put(topic, payload)
        logger.debug("message_published", topic=topic, size=len(payload))

    async def send_command(self, device_id: str, command: Command) -> None:
        """Send a command to a device.

        Args:
            device_id: Target device ID
            command: Command to send
        """
        topic = f"{self._settings.topic_prefix}/commands/{device_id}"
        await self.publish(topic, command.to_msgpack())
        logger.info(
            "command_sent",
            device_id=device_id,
            action=command.action,
            request_id=str(command.request_id),
        )

    async def query(self, selector: str, timeout_s: float = 5.0) -> list[tuple[str, bytes]]:
        """Query data from the Zenoh network.

        Args:
            selector: Query selector/topic pattern
            timeout_s: Query timeout in seconds

        Returns:
            List of (key, payload) tuples
        """
        if not self._session:
            raise RuntimeError("Zenoh session not started")

        results: list[tuple[str, bytes]] = []

        replies = self._session.get(selector, timeout=timeout_s)
        for reply in replies:
            if reply.ok:
                sample = reply.ok
                results.append((str(sample.key_expr), bytes(sample.payload)))

        return results

    @property
    def is_running(self) -> bool:
        """Check if the hub is running."""
        return self._running

    @property
    def session_id(self) -> str | None:
        """Get the Zenoh session ID."""
        if self._session:
            return str(self._session.zid())
        return None
