"""Herdbot client library for ESP32 (MicroPython).

Simple API for connecting ESP32 devices to the herdbot server.
Uses MQTT as transport with automatic server discovery.

Example:
    from herdbot import Device, Sensor

    device = Device(
        device_id="sensor-01",
        device_type="sensor_node",
        server="192.168.1.100"
    )

    imu = Sensor(device, "imu", sensor_type="imu_6dof")
    imu.publish({"accel": [0.1, 0.2, 9.8], "gyro": [0, 0, 0.1]})

    device.run()
"""

from .client import Device
from .sensors import Sensor
from .discovery import discover_server

__version__ = "0.1.0"

__all__ = ["Device", "Sensor", "discover_server"]
