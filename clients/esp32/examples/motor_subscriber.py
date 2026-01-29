"""Example: Motor control subscriber for ESP32.

Receives velocity commands and controls motors via PWM.

Hardware:
    - ESP32 board
    - L298N motor driver or similar
    - DC motors

Usage:
    1. Update WIFI_SSID and WIFI_PASSWORD
    2. Update SERVER_IP or use discovery
    3. Configure motor pins
    4. Upload to ESP32 and run
"""

import time

# Herdbot imports
from herdbot import Device
from herdbot.discovery import wait_for_wifi
from machine import PWM, Pin

# WiFi configuration
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"

# Server configuration (set to None for auto-discovery)
SERVER_IP = "192.168.1.100"

# Motor pin configuration (L298N example)
MOTOR_LEFT_EN = 13
MOTOR_LEFT_IN1 = 12
MOTOR_LEFT_IN2 = 14
MOTOR_RIGHT_EN = 27
MOTOR_RIGHT_IN1 = 26
MOTOR_RIGHT_IN2 = 25

# PWM frequency
PWM_FREQ = 1000


class MotorController:
    """Simple differential drive motor controller."""

    def __init__(self):
        # Left motor
        self.left_en = PWM(Pin(MOTOR_LEFT_EN), freq=PWM_FREQ, duty=0)
        self.left_in1 = Pin(MOTOR_LEFT_IN1, Pin.OUT)
        self.left_in2 = Pin(MOTOR_LEFT_IN2, Pin.OUT)

        # Right motor
        self.right_en = PWM(Pin(MOTOR_RIGHT_EN), freq=PWM_FREQ, duty=0)
        self.right_in1 = Pin(MOTOR_RIGHT_IN1, Pin.OUT)
        self.right_in2 = Pin(MOTOR_RIGHT_IN2, Pin.OUT)

        # Configuration
        self.max_speed = 1023  # Max PWM duty
        self.wheel_base = 0.2  # meters between wheels

        # Stop motors initially
        self.stop()

    def set_motor(self, motor: str, speed: float):
        """Set individual motor speed.

        Args:
            motor: "left" or "right"
            speed: -1.0 to 1.0 (negative = reverse)
        """
        speed = max(-1.0, min(1.0, speed))
        duty = int(abs(speed) * self.max_speed)

        if motor == "left":
            if speed >= 0:
                self.left_in1.value(1)
                self.left_in2.value(0)
            else:
                self.left_in1.value(0)
                self.left_in2.value(1)
            self.left_en.duty(duty)

        elif motor == "right":
            if speed >= 0:
                self.right_in1.value(1)
                self.right_in2.value(0)
            else:
                self.right_in1.value(0)
                self.right_in2.value(1)
            self.right_en.duty(duty)

    def set_velocity(self, linear: float, angular: float):
        """Set robot velocity using differential drive.

        Args:
            linear: Linear velocity in m/s
            angular: Angular velocity in rad/s
        """
        # Convert to wheel speeds
        # v_left = linear - (angular * wheel_base / 2)
        # v_right = linear + (angular * wheel_base / 2)

        v_left = linear - (angular * self.wheel_base / 2)
        v_right = linear + (angular * self.wheel_base / 2)

        # Normalize to -1..1 range (assuming max speed = 1 m/s)
        max_vel = 1.0
        self.set_motor("left", v_left / max_vel)
        self.set_motor("right", v_right / max_vel)

    def stop(self):
        """Stop all motors."""
        self.left_en.duty(0)
        self.right_en.duty(0)
        self.left_in1.value(0)
        self.left_in2.value(0)
        self.right_in1.value(0)
        self.right_in2.value(0)


def main():
    # Connect to WiFi
    if not wait_for_wifi(WIFI_SSID, WIFI_PASSWORD):
        print("WiFi connection failed")
        return

    # Initialize motor controller
    motors = MotorController()
    print("Motor controller initialized")

    # Create herdbot device
    device = Device(
        device_id="esp32-robot-01",
        device_type="mobile_robot",
        server=SERVER_IP,
        name="ESP32 Mobile Robot",
        capabilities=[
            {"name": "left_motor", "type": "motor", "config": {"max_speed": 1.0}},
            {"name": "right_motor", "type": "motor", "config": {"max_speed": 1.0}},
        ],
    )

    # Velocity command timeout (stop if no commands received)
    last_command_time = time.ticks_ms()
    command_timeout_ms = 500

    # Command handlers
    @device.on_command("move")
    def handle_move(params):
        """Handle move command with velocity."""
        nonlocal last_command_time

        linear = params.get("linear", 0)
        angular = params.get("angular", 0)

        motors.set_velocity(linear, angular)
        last_command_time = time.ticks_ms()

        return {"success": True, "linear": linear, "angular": angular}

    @device.on_command("stop")
    def handle_stop(params):
        """Handle stop command."""
        motors.stop()
        return {"success": True}

    @device.on_command("set_motor")
    def handle_set_motor(params):
        """Handle individual motor control."""
        nonlocal last_command_time

        motor = params.get("motor", "left")
        speed = params.get("speed", 0)

        motors.set_motor(motor, speed)
        last_command_time = time.ticks_ms()

        return {"success": True, "motor": motor, "speed": speed}

    # Connect to server
    if not device.connect():
        print("Connection failed")
        motors.stop()
        return

    print("Waiting for commands... (Ctrl+C to stop)")

    # Main loop
    try:
        while True:
            # Check for commands
            device._mqtt.check_msg()

            # Safety timeout - stop if no commands received
            now = time.ticks_ms()
            if time.ticks_diff(now, last_command_time) > command_timeout_ms:
                # Only stop if motors might be running
                motors.stop()

            # Small delay
            time.sleep_ms(10)

    except KeyboardInterrupt:
        pass
    finally:
        motors.stop()
        device.disconnect()
        print("Done")


if __name__ == "__main__":
    main()
