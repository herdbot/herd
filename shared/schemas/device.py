"""Device-related schema definitions for herdbot.

This module defines Pydantic models for device information, capabilities,
and status tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Self

import msgpack
from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """Standard device types."""

    ROBOT_ARM = "robot_arm"
    MOBILE_ROBOT = "mobile_robot"
    DRONE = "drone"
    SENSOR_NODE = "sensor_node"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CAMERA = "camera"
    CUSTOM = "custom"


class CapabilityType(str, Enum):
    """Types of device capabilities."""

    SENSOR = "sensor"
    ACTUATOR = "actuator"
    MOTOR = "motor"
    SERVO = "servo"
    CAMERA = "camera"
    SPEAKER = "speaker"
    DISPLAY = "display"
    GPIO = "gpio"
    COMMUNICATION = "communication"
    CUSTOM = "custom"


class ConnectionStatus(str, Enum):
    """Device connection status."""

    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ERROR = "error"
    UNKNOWN = "unknown"


class DeviceCapability(BaseModel):
    """Describes a single capability of a device.

    Attributes:
        name: Human-readable capability name
        capability_type: Type of capability
        config: Capability-specific configuration
        metadata: Additional metadata
    """

    name: str
    capability_type: CapabilityType
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}


class DeviceInfo(BaseModel):
    """Device registration and information.

    Attributes:
        device_id: Unique device identifier
        device_type: Type of device
        name: Human-readable device name
        capabilities: List of device capabilities
        firmware_version: Firmware/software version
        hardware_version: Hardware revision
        manufacturer: Device manufacturer
        model: Device model name
        metadata: Additional device metadata
    """

    device_id: str
    device_type: DeviceType
    name: str | None = None
    capabilities: list[DeviceCapability] = Field(default_factory=list)
    firmware_version: str = "0.0.0"
    hardware_version: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def to_msgpack(self) -> bytes:
        """Serialize to MessagePack format."""
        return msgpack.packb(self.model_dump(mode="json"))  # type: ignore[return-value]

    @classmethod
    def from_msgpack(cls, data: bytes) -> Self:
        """Deserialize from MessagePack format."""
        return cls.model_validate(msgpack.unpackb(data))


class DeviceStatus(BaseModel):
    """Current device status and health information.

    Attributes:
        device_id: Device identifier
        status: Connection status
        last_seen: Last heartbeat timestamp
        last_message: Last message timestamp
        uptime_ms: Device uptime in milliseconds
        error_count: Number of errors since last reset
        warning_count: Number of warnings since last reset
        battery_level: Battery percentage (0-100) if applicable
        signal_strength: Signal strength (0-100) if applicable
        ip_address: Device IP address if known
        extra: Additional status fields
    """

    device_id: str
    status: ConnectionStatus = ConnectionStatus.UNKNOWN
    last_seen: datetime | None = None
    last_message: datetime | None = None
    uptime_ms: int = 0
    error_count: int = 0
    warning_count: int = 0
    battery_level: int | None = Field(default=None, ge=0, le=100)
    signal_strength: int | None = Field(default=None, ge=0, le=100)
    ip_address: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"use_enum_values": True}

    def is_online(self) -> bool:
        """Check if device is currently online."""
        return self.status == ConnectionStatus.ONLINE

    def to_msgpack(self) -> bytes:
        """Serialize to MessagePack format."""
        return msgpack.packb(self.model_dump(mode="json"))  # type: ignore[return-value]

    @classmethod
    def from_msgpack(cls, data: bytes) -> Self:
        """Deserialize from MessagePack format."""
        return cls.model_validate(msgpack.unpackb(data))
