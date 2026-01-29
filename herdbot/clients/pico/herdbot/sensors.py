"""Sensor helpers for herdbot (MicroPython/Pico W)."""


class Sensor:
    """Generic sensor wrapper."""

    def __init__(self, device, sensor_id: str, sensor_type: str = "custom", unit: str = ""):
        self.device = device
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.unit = unit
        device._sensors[sensor_id] = self

    def publish(self, value):
        """Publish sensor reading."""
        self.device.publish_sensor(
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type,
            value=value,
            unit=self.unit,
        )


class DistanceSensor(Sensor):
    """Distance sensor helper."""

    def __init__(self, device, sensor_id: str = "distance", unit: str = "mm"):
        super().__init__(device, sensor_id, sensor_type="distance", unit=unit)

    def publish_mm(self, distance_mm: float):
        self.publish(distance_mm)


class TemperatureSensor(Sensor):
    """Temperature sensor helper."""

    def __init__(self, device, sensor_id: str = "temp", unit: str = "C"):
        super().__init__(device, sensor_id, sensor_type="temperature", unit=unit)

    def publish_celsius(self, temp_c: float):
        self.publish(temp_c)
