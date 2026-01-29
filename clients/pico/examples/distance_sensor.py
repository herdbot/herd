"""Example: Distance sensor for Pico W.

Reads distance from HC-SR04 ultrasonic sensor and publishes to herdbot.

Hardware:
    - Raspberry Pi Pico W
    - HC-SR04 ultrasonic sensor
        - VCC -> 3.3V or 5V
        - GND -> GND
        - TRIG -> GP2
        - ECHO -> GP3

Usage:
    1. Update WIFI_SSID and WIFI_PASSWORD
    2. Update SERVER_IP
    3. Upload to Pico W and run
"""

import time
import network
from machine import Pin

from herdbot import Device
from herdbot.sensors import DistanceSensor

# WiFi configuration
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"

# Server configuration
SERVER_IP = "192.168.1.100"

# Sensor pins
TRIG_PIN = 2
ECHO_PIN = 3


class HCSR04:
    """HC-SR04 ultrasonic distance sensor driver."""

    def __init__(self, trig_pin: int, echo_pin: int):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.trig.value(0)

    def measure_mm(self) -> float:
        """Measure distance in millimeters.

        Returns:
            Distance in mm, or -1 if timeout
        """
        # Send trigger pulse
        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)

        # Wait for echo start
        timeout = time.ticks_us() + 30000  # 30ms timeout
        while self.echo.value() == 0:
            if time.ticks_us() > timeout:
                return -1
            start = time.ticks_us()

        # Wait for echo end
        while self.echo.value() == 1:
            if time.ticks_us() > timeout:
                return -1
            end = time.ticks_us()

        # Calculate distance
        # Speed of sound = 343 m/s = 0.343 mm/us
        # Distance = (time * speed) / 2 (round trip)
        duration = time.ticks_diff(end, start)
        distance_mm = (duration * 0.343) / 2

        return distance_mm


def connect_wifi():
    """Connect to WiFi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    print(f"Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 30
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if wlan.isconnected():
        print(f"Connected: {wlan.ifconfig()[0]}")
        return True
    else:
        print("WiFi connection failed")
        return False


def main():
    # Connect to WiFi
    if not connect_wifi():
        return

    # Initialize sensor
    sensor = HCSR04(TRIG_PIN, ECHO_PIN)
    print("HC-SR04 initialized")

    # Create herdbot device
    device = Device(
        device_id="pico-distance-01",
        device_type="sensor_node",
        server=SERVER_IP,
        name="Pico Distance Sensor",
        capabilities=[
            {"name": "distance", "type": "sensor", "config": {"range_mm": 4000}}
        ],
    )

    # Create distance sensor
    dist_sensor = DistanceSensor(device, "hcsr04")

    # Moving average filter
    readings = []
    filter_size = 5

    # Command handler
    @device.on_command("get_reading")
    def handle_get_reading(params):
        distance = sensor.measure_mm()
        return {"distance_mm": distance}

    # Connect
    if not device.connect():
        print("Connection failed")
        return

    print("Publishing distance data... (Ctrl+C to stop)")

    # Main loop
    last_publish = 0
    publish_interval_ms = 100  # 10 Hz

    try:
        while True:
            device._mqtt.check_msg()

            now = time.ticks_ms()
            if time.ticks_diff(now, last_publish) >= publish_interval_ms:
                distance = sensor.measure_mm()

                if distance > 0:
                    # Apply moving average filter
                    readings.append(distance)
                    if len(readings) > filter_size:
                        readings.pop(0)

                    filtered = sum(readings) / len(readings)
                    dist_sensor.publish_mm(filtered)

                last_publish = now

            time.sleep_ms(10)

    except KeyboardInterrupt:
        pass
    finally:
        device.disconnect()
        print("Done")


if __name__ == "__main__":
    main()
