"""Sensor helper classes for herdbot (MicroPython/ESP32).

Provides easy-to-use wrappers for common sensor types.
"""


class Sensor:
    """Generic sensor wrapper.

    Example:
        imu = Sensor(device, "imu", sensor_type="imu_6dof", unit="m/s^2,rad/s")
        imu.publish({"accel": [0.1, 0.2, 9.8], "gyro": [0, 0, 0.1]})
    """

    def __init__(self, device, sensor_id: str, sensor_type: str = "custom", unit: str = ""):
        """Initialize sensor.

        Args:
            device: Parent Device instance
            sensor_id: Unique sensor identifier on this device
            sensor_type: Type of sensor (temperature, imu_6dof, distance, etc.)
            unit: Unit of measurement
        """
        self.device = device
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.unit = unit

        # Register with device
        device._sensors[sensor_id] = self

    def publish(self, value):
        """Publish a sensor reading.

        Args:
            value: Sensor value (number, list, or dict)
        """
        self.device.publish_sensor(
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type,
            value=value,
            unit=self.unit,
        )


class TemperatureSensor(Sensor):
    """Temperature sensor helper."""

    def __init__(self, device, sensor_id: str = "temp", unit: str = "C"):
        super().__init__(device, sensor_id, sensor_type="temperature", unit=unit)

    def publish_celsius(self, temp_c: float):
        """Publish temperature in Celsius."""
        self.publish(temp_c)

    def publish_fahrenheit(self, temp_f: float):
        """Publish temperature in Fahrenheit (converted to Celsius)."""
        temp_c = (temp_f - 32) * 5 / 9
        self.publish(temp_c)


class DistanceSensor(Sensor):
    """Distance/range sensor helper."""

    def __init__(self, device, sensor_id: str = "distance", unit: str = "mm"):
        super().__init__(device, sensor_id, sensor_type="distance", unit=unit)

    def publish_mm(self, distance_mm: float):
        """Publish distance in millimeters."""
        self.publish(distance_mm)

    def publish_cm(self, distance_cm: float):
        """Publish distance in centimeters (converted to mm)."""
        self.publish(distance_cm * 10)


class IMUSensor(Sensor):
    """6DOF/9DOF IMU sensor helper."""

    def __init__(self, device, sensor_id: str = "imu", dof: int = 6):
        sensor_type = f"imu_{dof}dof"
        super().__init__(device, sensor_id, sensor_type=sensor_type, unit="m/s^2,rad/s")
        self.dof = dof

    def publish_raw(self, accel: list, gyro: list, mag: list = None):
        """Publish raw IMU readings.

        Args:
            accel: Accelerometer [x, y, z] in m/s^2
            gyro: Gyroscope [x, y, z] in rad/s
            mag: Magnetometer [x, y, z] in uT (for 9DOF)
        """
        data = {
            "accel": accel,
            "gyro": gyro,
        }
        if mag and self.dof == 9:
            data["mag"] = mag
        self.publish(data)


class EncoderSensor(Sensor):
    """Rotary encoder sensor helper."""

    def __init__(self, device, sensor_id: str = "encoder", unit: str = "ticks"):
        super().__init__(device, sensor_id, sensor_type="encoder", unit=unit)
        self._last_count = 0

    def publish_count(self, count: int):
        """Publish encoder count."""
        self.publish(count)

    def publish_delta(self, count: int):
        """Publish encoder delta since last reading."""
        delta = count - self._last_count
        self._last_count = count
        self.publish({"count": count, "delta": delta})


class BatterySensor(Sensor):
    """Battery level sensor helper."""

    def __init__(self, device, sensor_id: str = "battery"):
        super().__init__(device, sensor_id, sensor_type="battery", unit="%")

    def publish_percentage(self, percentage: float):
        """Publish battery percentage (0-100)."""
        self.publish(max(0, min(100, percentage)))

    def publish_voltage(self, voltage: float, min_v: float = 3.0, max_v: float = 4.2):
        """Publish battery voltage (converted to percentage)."""
        percentage = ((voltage - min_v) / (max_v - min_v)) * 100
        self.publish_percentage(percentage)


class GPSSensor(Sensor):
    """GPS sensor helper."""

    def __init__(self, device, sensor_id: str = "gps"):
        super().__init__(device, sensor_id, sensor_type="gps", unit="deg")

    def publish_position(
        self,
        latitude: float,
        longitude: float,
        altitude: float = None,
        speed: float = None,
        heading: float = None,
        hdop: float = None,
    ):
        """Publish GPS position.

        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            altitude: Altitude in meters (optional)
            speed: Ground speed in m/s (optional)
            heading: Heading in degrees (optional)
            hdop: Horizontal dilution of precision (optional)
        """
        data = {
            "lat": latitude,
            "lon": longitude,
        }
        if altitude is not None:
            data["alt"] = altitude
        if speed is not None:
            data["speed"] = speed
        if heading is not None:
            data["heading"] = heading
        if hdop is not None:
            data["hdop"] = hdop

        self.publish(data)
