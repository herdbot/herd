"""Message type definitions for herdbot communication.

This module defines Pydantic models for all standard message types used
in the herdbot messaging system. Messages are serialized using MessagePack
with JSON fallback.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Self
from uuid import UUID, uuid4

import msgpack
from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    """Base class for all messages with common fields."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def to_msgpack(self) -> bytes:
        """Serialize message to MessagePack format."""
        data = self.model_dump(mode="json")
        return msgpack.packb(data)

    @classmethod
    def from_msgpack(cls, data: bytes) -> Self:
        """Deserialize message from MessagePack format."""
        return cls.model_validate(msgpack.unpackb(data))

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str | bytes) -> Self:
        """Deserialize message from JSON string."""
        return cls.model_validate_json(data)


class SensorType(str, Enum):
    """Standard sensor types."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    DISTANCE = "distance"
    LIGHT = "light"
    IMU_6DOF = "imu_6dof"
    IMU_9DOF = "imu_9dof"
    GPS = "gps"
    CAMERA = "camera"
    LIDAR = "lidar"
    ENCODER = "encoder"
    BATTERY = "battery"
    CUSTOM = "custom"


class SensorReading(MessageBase):
    """Sensor data reading from a device.

    Attributes:
        device_id: Unique identifier of the source device
        sensor_type: Type of sensor (temperature, imu, etc.)
        sensor_id: Optional identifier for specific sensor on device
        value: The sensor reading value(s)
        unit: Unit of measurement
        quality: Data quality indicator (0.0-1.0)
    """

    device_id: str
    sensor_type: SensorType
    sensor_id: str | None = None
    value: float | list[float] | dict[str, Any]
    unit: str
    quality: float = Field(default=1.0, ge=0.0, le=1.0)


class Pose2D(MessageBase):
    """2D pose representation for ground robots.

    Attributes:
        x: X position in meters
        y: Y position in meters
        theta: Orientation in radians (-pi to pi)
        frame_id: Reference frame identifier
        covariance: Optional 3x3 covariance matrix [xx, xy, xt, yy, yt, tt]
    """

    x: float
    y: float
    theta: float = Field(ge=-3.14159, le=3.14159)
    frame_id: str = "world"
    covariance: list[float] | None = None


class Twist2D(MessageBase):
    """2D velocity command for differential drive robots.

    Attributes:
        linear_vel: Linear velocity in m/s
        angular_vel: Angular velocity in rad/s
        device_id: Target device identifier
    """

    linear_vel: float
    angular_vel: float
    device_id: str | None = None


class Command(MessageBase):
    """Command message to control a device.

    Attributes:
        device_id: Target device identifier
        action: Action name to execute
        params: Action parameters
        request_id: Unique request identifier for tracking responses
        priority: Command priority (higher = more urgent)
        timeout_ms: Command timeout in milliseconds
    """

    device_id: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    request_id: UUID = Field(default_factory=uuid4)
    priority: int = Field(default=0, ge=0, le=10)
    timeout_ms: int = Field(default=5000, ge=0)


class CommandResponse(MessageBase):
    """Response to a command execution.

    Attributes:
        request_id: Original request identifier
        success: Whether the command succeeded
        result: Result data if successful
        error: Error message if failed
        execution_time_ms: Time taken to execute
    """

    request_id: UUID
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int | None = None


class Heartbeat(MessageBase):
    """Device heartbeat message for presence detection.

    Attributes:
        device_id: Device identifier
        sequence: Monotonically increasing sequence number
        uptime_ms: Device uptime in milliseconds
        load: CPU/resource load (0.0-1.0)
        memory_free: Free memory in bytes
    """

    device_id: str
    sequence: int = Field(ge=0)
    uptime_ms: int = Field(ge=0)
    load: float = Field(default=0.0, ge=0.0, le=1.0)
    memory_free: int | None = None
