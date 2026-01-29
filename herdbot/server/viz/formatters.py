"""Data formatters for Rerun visualization.

Converts herdbot message types to Rerun-compatible formats.
"""

from typing import Any

from shared.schemas import Pose2D, SensorReading, DeviceStatus
from shared.schemas.device import SensorType, ConnectionStatus


def format_sensor_reading(reading: SensorReading) -> dict[str, Any]:
    """Format a sensor reading for Rerun visualization.

    Args:
        reading: Sensor reading to format

    Returns:
        Dictionary with visualization type and formatted data
    """
    sensor_type = reading.sensor_type
    value = reading.value

    # Temperature, humidity, pressure, light, battery - scalar values
    if sensor_type in (
        SensorType.TEMPERATURE,
        SensorType.HUMIDITY,
        SensorType.PRESSURE,
        SensorType.LIGHT,
        SensorType.BATTERY,
    ):
        if isinstance(value, (int, float)):
            return {"type": "scalar", "value": float(value), "unit": reading.unit}
        elif isinstance(value, dict):
            # Take first numeric value
            for v in value.values():
                if isinstance(v, (int, float)):
                    return {"type": "scalar", "value": float(v), "unit": reading.unit}

    # Distance sensor
    if sensor_type == SensorType.DISTANCE:
        if isinstance(value, (int, float)):
            return {"type": "scalar", "value": float(value), "unit": reading.unit}
        elif isinstance(value, list) and len(value) >= 1:
            return {"type": "scalar", "value": float(value[0]), "unit": reading.unit}

    # IMU sensors
    if sensor_type in (SensorType.IMU_6DOF, SensorType.IMU_9DOF):
        if isinstance(value, dict):
            accel = value.get("accel", [0, 0, 0])
            gyro = value.get("gyro", [0, 0, 0])
            mag = value.get("mag", [0, 0, 0]) if sensor_type == SensorType.IMU_9DOF else None

            return {
                "type": "imu",
                "accel": accel[:3] if len(accel) >= 3 else accel + [0] * (3 - len(accel)),
                "gyro": gyro[:3] if len(gyro) >= 3 else gyro + [0] * (3 - len(gyro)),
                "mag": mag[:3] if mag and len(mag) >= 3 else None,
            }

    # GPS
    if sensor_type == SensorType.GPS:
        if isinstance(value, dict):
            return {
                "type": "gps",
                "lat": value.get("lat", 0),
                "lon": value.get("lon", 0),
                "alt": value.get("alt"),
                "speed": value.get("speed"),
                "heading": value.get("heading"),
            }

    # Encoder
    if sensor_type == SensorType.ENCODER:
        if isinstance(value, (int, float)):
            return {"type": "scalar", "value": float(value), "unit": "ticks"}
        elif isinstance(value, dict):
            return {
                "type": "scalar",
                "value": float(value.get("count", value.get("delta", 0))),
                "unit": "ticks",
            }

    # Generic/custom - try to extract a scalar
    if isinstance(value, (int, float)):
        return {"type": "scalar", "value": float(value), "unit": reading.unit}
    elif isinstance(value, list):
        if len(value) == 3:
            return {"type": "vector3", "value": value}
        elif len(value) >= 1:
            return {"type": "scalar", "value": float(value[0]), "unit": reading.unit}
    elif isinstance(value, dict):
        # Try to find a numeric value
        for k, v in value.items():
            if isinstance(v, (int, float)):
                return {"type": "scalar", "value": float(v), "unit": reading.unit}

    # Fallback
    return {"type": "unknown", "value": str(value)}


def format_pose(pose: Pose2D) -> dict[str, Any]:
    """Format a 2D pose for Rerun visualization.

    Args:
        pose: Pose to format

    Returns:
        Dictionary with formatted pose data
    """
    return {
        "x": pose.x,
        "y": pose.y,
        "theta": pose.theta,
        "frame_id": pose.frame_id,
        "covariance": pose.covariance,
    }


def format_device_status(status: DeviceStatus) -> dict[str, Any]:
    """Format device status for visualization.

    Args:
        status: Device status to format

    Returns:
        Dictionary with formatted status data
    """
    # Map status to color
    status_colors = {
        ConnectionStatus.ONLINE: [0, 255, 0],      # Green
        ConnectionStatus.OFFLINE: [255, 0, 0],     # Red
        ConnectionStatus.CONNECTING: [255, 255, 0], # Yellow
        ConnectionStatus.ERROR: [255, 128, 0],     # Orange
        ConnectionStatus.UNKNOWN: [128, 128, 128], # Gray
    }

    return {
        "device_id": status.device_id,
        "status": status.status.value if isinstance(status.status, ConnectionStatus) else status.status,
        "color": status_colors.get(status.status, [128, 128, 128]),
        "uptime_ms": status.uptime_ms,
        "battery_level": status.battery_level,
        "signal_strength": status.signal_strength,
        "last_seen": status.last_seen.isoformat() if status.last_seen else None,
    }


def format_twist_for_arrow(linear_vel: float, angular_vel: float, scale: float = 1.0) -> dict[str, Any]:
    """Format a twist command as an arrow for visualization.

    Args:
        linear_vel: Linear velocity
        angular_vel: Angular velocity
        scale: Arrow scale factor

    Returns:
        Dictionary with arrow visualization data
    """
    import math

    # Represent as arrow from origin
    # Length proportional to linear velocity
    # Curvature based on angular velocity

    length = abs(linear_vel) * scale
    angle = angular_vel * 0.5  # Scale angular for visualization

    dx = length * math.cos(angle)
    dy = length * math.sin(angle)

    return {
        "origin": [0, 0],
        "vector": [dx, dy],
        "color": [0, 128, 255] if linear_vel >= 0 else [255, 128, 0],
    }
