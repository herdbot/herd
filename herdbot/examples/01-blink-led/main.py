"""Example 01: Blink LED with Herdbot

The simplest possible herdbot example.
Blinks an LED and reports state to the server.

Hardware:
    - ESP32 or Pico W
    - LED connected to GPIO 2 (or built-in LED)

This example demonstrates:
    - Basic device setup
    - Command handling
    - Sensor publishing
"""

import time

try:
    from machine import Pin
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    print("Running in simulation mode (no hardware)")

# Herdbot client
from herdbot import Device
from herdbot.sensors import Sensor

# Configuration
DEVICE_ID = "blink-led-01"
SERVER_IP = "192.168.1.100"  # Change to your server
LED_PIN = 2


def main():
    # Set up LED (or simulate)
    if MICROPYTHON:
        led = Pin(LED_PIN, Pin.OUT)
    else:
        class FakeLED:
            def __init__(self):
                self._value = 0
            def value(self, v=None):
                if v is None:
                    return self._value
                self._value = v
                print(f"LED: {'ON' if v else 'OFF'}")
        led = FakeLED()

    # Create herdbot device
    device = Device(
        device_id=DEVICE_ID,
        device_type="sensor_node",
        server=SERVER_IP if MICROPYTHON else None,
        name="Blink LED Example",
        capabilities=[
            {"name": "led", "type": "actuator", "config": {"pin": LED_PIN}}
        ],
    )

    # Create sensor to report LED state
    led_state = Sensor(device, "led_state", sensor_type="custom", unit="bool")

    # Track state
    current_state = False
    blink_enabled = True
    blink_interval = 1.0  # seconds

    # Command handlers
    @device.on_command("set_led")
    def handle_set_led(params):
        """Set LED to specific state."""
        nonlocal current_state
        state = params.get("state", False)
        led.value(1 if state else 0)
        current_state = state
        return {"state": current_state}

    @device.on_command("toggle")
    def handle_toggle(params):
        """Toggle LED state."""
        nonlocal current_state
        current_state = not current_state
        led.value(1 if current_state else 0)
        return {"state": current_state}

    @device.on_command("set_blink")
    def handle_set_blink(params):
        """Enable/disable blinking."""
        nonlocal blink_enabled, blink_interval
        blink_enabled = params.get("enabled", True)
        blink_interval = params.get("interval", 1.0)
        return {"enabled": blink_enabled, "interval": blink_interval}

    # Connect (skip if no server)
    if MICROPYTHON:
        from herdbot.discovery import wait_for_wifi
        # wait_for_wifi("YourSSID", "YourPassword")

        if not device.connect():
            print("Connection failed, running offline")

    print(f"Blink LED example running (device: {DEVICE_ID})")
    print("Commands: set_led, toggle, set_blink")

    # Main loop
    last_blink = time.time() if hasattr(time, 'time') else 0
    last_publish = 0

    try:
        while True:
            now = time.time() if hasattr(time, 'time') else time.ticks_ms() / 1000

            # Handle blinking
            if blink_enabled and (now - last_blink) >= blink_interval:
                current_state = not current_state
                led.value(1 if current_state else 0)
                last_blink = now

            # Publish state periodically
            if (now - last_publish) >= 0.5:
                led_state.publish(1 if current_state else 0)
                last_publish = now

            # Check for commands (if connected)
            if MICROPYTHON and device._mqtt and device._connected:
                device._mqtt.check_msg()

            # Small delay
            if MICROPYTHON:
                time.sleep_ms(50)
            else:
                time.sleep(0.05)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        led.value(0)
        if MICROPYTHON:
            device.disconnect()
        print("Done")


if __name__ == "__main__":
    main()
