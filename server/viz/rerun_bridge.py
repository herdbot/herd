"""Rerun visualization bridge for herdbot.

Subscribes to Zenoh topics and forwards data to Rerun for visualization.
"""

from typing import Any

import structlog

try:
    import rerun as rr
    RERUN_AVAILABLE = True
except ImportError:
    RERUN_AVAILABLE = False
    rr = None

from shared.schemas import Pose2D, SensorReading

from .formatters import format_pose, format_sensor_reading

logger = structlog.get_logger()


class RerunBridge:
    """Bridge between Zenoh messages and Rerun visualization.

    Subscribes to relevant topics and logs data to Rerun for
    real-time visualization.
    """

    def __init__(
        self,
        recording_id: str = "herdbot",
        spawn: bool = True,
    ) -> None:
        """Initialize the Rerun bridge.

        Args:
            recording_id: Rerun recording/application ID
            spawn: Whether to spawn the Rerun viewer
        """
        self._recording_id = recording_id
        self._spawn = spawn
        self._initialized = False
        self._running = False

        # Track time series for each sensor
        self._timeseries: dict[str, list[tuple[float, float]]] = {}

    async def start(self) -> bool:
        """Start the Rerun bridge.

        Returns:
            True if started successfully
        """
        if not RERUN_AVAILABLE:
            logger.warning("rerun_not_available", message="Install rerun-sdk to enable visualization")
            return False

        if self._initialized:
            return True

        try:
            # Initialize Rerun
            rr.init(self._recording_id, spawn=self._spawn)

            # Set up entity paths
            rr.log("world", rr.ViewCoordinates.RIGHT_HAND_Z_UP, static=True)

            self._initialized = True
            self._running = True

            logger.info("rerun_bridge_started", recording_id=self._recording_id)
            return True

        except Exception as e:
            logger.error("rerun_init_failed", error=str(e))
            return False

    async def stop(self) -> None:
        """Stop the Rerun bridge."""
        self._running = False
        logger.info("rerun_bridge_stopped")

    def log_sensor_reading(self, reading: SensorReading) -> None:
        """Log a sensor reading to Rerun.

        Args:
            reading: Sensor reading to visualize
        """
        if not self._initialized or not RERUN_AVAILABLE:
            return

        entity_path = f"devices/{reading.device_id}/sensors/{reading.sensor_id or reading.sensor_type}"

        try:
            # Format and log based on sensor type
            log_data = format_sensor_reading(reading)

            if log_data["type"] == "scalar":
                rr.log(entity_path, rr.Scalar(log_data["value"]))

            elif log_data["type"] == "vector3":
                rr.log(entity_path, rr.Points3D([log_data["value"]]))

            elif log_data["type"] == "imu":
                # Log accelerometer
                rr.log(
                    f"{entity_path}/accel",
                    rr.Points3D([log_data["accel"]]),
                )
                # Log gyroscope
                rr.log(
                    f"{entity_path}/gyro",
                    rr.Points3D([log_data["gyro"]]),
                )

            elif log_data["type"] == "gps":
                # Log GPS as 2D point on map
                rr.log(
                    f"{entity_path}/position",
                    rr.Points2D([[log_data["lon"], log_data["lat"]]]),
                )

            # Track time series
            self._update_timeseries(entity_path, reading.timestamp.timestamp(), log_data)

        except Exception as e:
            logger.error("rerun_log_error", entity=entity_path, error=str(e))

    def log_pose(self, device_id: str, pose: Pose2D) -> None:
        """Log a 2D pose to Rerun.

        Args:
            device_id: Device identifier
            pose: 2D pose to visualize
        """
        if not self._initialized or not RERUN_AVAILABLE:
            return

        entity_path = f"devices/{device_id}/pose"

        try:
            log_data = format_pose(pose)

            # Log position as 2D point
            rr.log(
                f"{entity_path}/position",
                rr.Points2D([[log_data["x"], log_data["y"]]]),
            )

            # Log orientation as arrow
            import math
            dx = math.cos(log_data["theta"]) * 0.5
            dy = math.sin(log_data["theta"]) * 0.5

            rr.log(
                f"{entity_path}/heading",
                rr.Arrows2D(
                    origins=[[log_data["x"], log_data["y"]]],
                    vectors=[[dx, dy]],
                ),
            )

        except Exception as e:
            logger.error("rerun_pose_error", entity=entity_path, error=str(e))

    def log_device_status(self, device_id: str, status: dict[str, Any]) -> None:
        """Log device status as text annotation.

        Args:
            device_id: Device identifier
            status: Status information
        """
        if not self._initialized or not RERUN_AVAILABLE:
            return

        entity_path = f"devices/{device_id}/status"

        try:
            status_text = f"Status: {status.get('status', 'unknown')}"
            if status.get('battery_level') is not None:
                status_text += f" | Battery: {status['battery_level']}%"

            rr.log(entity_path, rr.TextLog(status_text))

        except Exception as e:
            logger.error("rerun_status_error", entity=entity_path, error=str(e))

    def log_command(self, device_id: str, action: str, params: dict[str, Any]) -> None:
        """Log a command for debugging.

        Args:
            device_id: Target device
            action: Command action
            params: Command parameters
        """
        if not self._initialized or not RERUN_AVAILABLE:
            return

        entity_path = f"devices/{device_id}/commands"

        try:
            rr.log(entity_path, rr.TextLog(f"Command: {action} - {params}"))
        except Exception as e:
            logger.error("rerun_command_error", entity=entity_path, error=str(e))

    def log_ai_response(self, response: str, provider: str) -> None:
        """Log AI response.

        Args:
            response: AI response text
            provider: AI provider name
        """
        if not self._initialized or not RERUN_AVAILABLE:
            return

        try:
            rr.log("ai/responses", rr.TextLog(f"[{provider}] {response}"))
        except Exception as e:
            logger.error("rerun_ai_error", error=str(e))

    def _update_timeseries(
        self, entity_path: str, timestamp: float, data: dict[str, Any]
    ) -> None:
        """Track time series data for trend visualization."""
        key = entity_path

        if key not in self._timeseries:
            self._timeseries[key] = []

        # Extract scalar value if available
        if "value" in data and isinstance(data["value"], (int, float)):
            self._timeseries[key].append((timestamp, data["value"]))

            # Keep last 1000 points
            if len(self._timeseries[key]) > 1000:
                self._timeseries[key] = self._timeseries[key][-1000:]

    @property
    def is_available(self) -> bool:
        """Check if Rerun is available."""
        return RERUN_AVAILABLE

    @property
    def is_running(self) -> bool:
        """Check if bridge is running."""
        return self._running
