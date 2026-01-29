"""Herdbot client library for Raspberry Pi Pico W (MicroPython).

Simple API for connecting Pico W devices to the herdbot server.
Uses MQTT as transport with automatic server discovery.

Example:
    from herdbot import Device, Sensor

    device = Device(
        device_id="pico-sensor-01",
        device_type="sensor_node",
        server="192.168.1.100"
    )

    distance = Sensor(device, "distance", sensor_type="distance", unit="mm")
    distance.publish(150.5)

    device.run()
"""

from .client import Device
from .sensors import Sensor, DistanceSensor, TemperatureSensor

__version__ = "0.1.0"

__all__ = ["Device", "Sensor", "DistanceSensor", "TemperatureSensor"]
