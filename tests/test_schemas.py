"""Tests for message schemas."""

from datetime import datetime
from uuid import UUID

import pytest

from shared.schemas import (
    Command,
    CommandResponse,
    ConnectionStatus,
    DeviceInfo,
    DeviceStatus,
    DeviceType,
    Pose2D,
    SensorReading,
    SensorType,
)


class TestSensorReading:
    """Tests for SensorReading schema."""

    def test_create_temperature_reading(self):
        reading = SensorReading(
            device_id="sensor-01",
            sensor_type=SensorType.TEMPERATURE,
            value=23.5,
            unit="C",
        )

        assert reading.device_id == "sensor-01"
        assert reading.sensor_type == SensorType.TEMPERATURE
        assert reading.value == 23.5
        assert reading.unit == "C"
        assert reading.quality == 1.0
        assert reading.timestamp is not None

    def test_create_imu_reading(self):
        reading = SensorReading(
            device_id="robot-01",
            sensor_type=SensorType.IMU_6DOF,
            value={"accel": [0.1, 0.2, 9.8], "gyro": [0, 0, 0.1]},
            unit="m/s^2,rad/s",
        )

        assert reading.sensor_type == SensorType.IMU_6DOF
        assert "accel" in reading.value
        assert "gyro" in reading.value

    def test_msgpack_serialization(self):
        reading = SensorReading(
            device_id="test",
            sensor_type=SensorType.DISTANCE,
            value=150.0,
            unit="mm",
        )

        packed = reading.to_msgpack()
        assert isinstance(packed, bytes)

        unpacked = SensorReading.from_msgpack(packed)
        assert unpacked.device_id == reading.device_id
        assert unpacked.value == reading.value


class TestPose2D:
    """Tests for Pose2D schema."""

    def test_create_pose(self):
        pose = Pose2D(x=1.0, y=2.0, theta=0.5)

        assert pose.x == 1.0
        assert pose.y == 2.0
        assert pose.theta == 0.5
        assert pose.frame_id == "world"

    def test_theta_bounds(self):
        with pytest.raises(ValueError):
            Pose2D(x=0, y=0, theta=4.0)  # > pi

        with pytest.raises(ValueError):
            Pose2D(x=0, y=0, theta=-4.0)  # < -pi


class TestCommand:
    """Tests for Command schema."""

    def test_create_command(self):
        cmd = Command(
            device_id="robot-01",
            action="move",
            params={"linear": 0.5, "angular": 0},
        )

        assert cmd.device_id == "robot-01"
        assert cmd.action == "move"
        assert cmd.params["linear"] == 0.5
        assert isinstance(cmd.request_id, UUID)

    def test_command_response(self):
        cmd = Command(device_id="test", action="test")

        response = CommandResponse(
            request_id=cmd.request_id,
            success=True,
            result={"data": "value"},
        )

        assert response.request_id == cmd.request_id
        assert response.success is True
        assert response.error is None


class TestDeviceInfo:
    """Tests for DeviceInfo schema."""

    def test_create_device(self):
        device = DeviceInfo(
            device_id="robot-01",
            device_type=DeviceType.MOBILE_ROBOT,
            name="Test Robot",
            firmware_version="1.0.0",
        )

        assert device.device_id == "robot-01"
        assert device.device_type == DeviceType.MOBILE_ROBOT
        assert device.name == "Test Robot"

    def test_msgpack_serialization(self):
        device = DeviceInfo(
            device_id="test",
            device_type=DeviceType.SENSOR_NODE,
        )

        packed = device.to_msgpack()
        unpacked = DeviceInfo.from_msgpack(packed)

        assert unpacked.device_id == device.device_id


class TestDeviceStatus:
    """Tests for DeviceStatus schema."""

    def test_online_status(self):
        status = DeviceStatus(
            device_id="test",
            status=ConnectionStatus.ONLINE,
            last_seen=datetime.utcnow(),
        )

        assert status.is_online() is True

    def test_offline_status(self):
        status = DeviceStatus(
            device_id="test",
            status=ConnectionStatus.OFFLINE,
        )

        assert status.is_online() is False
