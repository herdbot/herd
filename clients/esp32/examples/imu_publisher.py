"""Example: IMU sensor publisher for ESP32.

Reads IMU data from an MPU6050 and publishes to herdbot server.

Hardware:
    - ESP32 board
    - MPU6050 IMU connected via I2C (SDA=21, SCL=22)

Usage:
    1. Update WIFI_SSID and WIFI_PASSWORD
    2. Update SERVER_IP or use discovery
    3. Upload to ESP32 and run
"""

import time

# Herdbot imports
from herdbot import Device
from herdbot.discovery import wait_for_wifi
from herdbot.sensors import IMUSensor
from machine import I2C, Pin

# WiFi configuration
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"

# Server configuration (set to None for auto-discovery)
SERVER_IP = "192.168.1.100"

# I2C configuration
I2C_SDA = 21
I2C_SCL = 22
MPU6050_ADDR = 0x68


class MPU6050:
    """Simple MPU6050 driver."""

    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr

        # Wake up the MPU6050
        self.i2c.writeto_mem(self.addr, 0x6B, b'\x00')
        time.sleep(0.1)

    def read_raw(self) -> tuple:
        """Read raw accelerometer and gyroscope values."""
        data = self.i2c.readfrom_mem(self.addr, 0x3B, 14)

        ax = self._bytes_to_int(data[0:2]) / 16384.0
        ay = self._bytes_to_int(data[2:4]) / 16384.0
        az = self._bytes_to_int(data[4:6]) / 16384.0

        gx = self._bytes_to_int(data[8:10]) / 131.0
        gy = self._bytes_to_int(data[10:12]) / 131.0
        gz = self._bytes_to_int(data[12:14]) / 131.0

        return (ax, ay, az, gx, gy, gz)

    def _bytes_to_int(self, data: bytes) -> int:
        value = (data[0] << 8) | data[1]
        if value >= 0x8000:
            value -= 0x10000
        return value


def main():
    # Connect to WiFi
    if not wait_for_wifi(WIFI_SSID, WIFI_PASSWORD):
        print("WiFi connection failed")
        return

    # Initialize I2C and IMU
    i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400000)
    imu = MPU6050(i2c, MPU6050_ADDR)
    print("MPU6050 initialized")

    # Create herdbot device
    device = Device(
        device_id="esp32-imu-01",
        device_type="sensor_node",
        server=SERVER_IP,
        name="ESP32 IMU Sensor",
        capabilities=[
            {"name": "imu", "type": "sensor", "config": {"dof": 6}}
        ],
    )

    # Create IMU sensor
    imu_sensor = IMUSensor(device, "mpu6050", dof=6)

    # Command handler for calibration
    @device.on_command("calibrate")
    def handle_calibrate(params):
        print("Calibrating IMU...")
        # Simple calibration: take average of several readings
        samples = 100
        ax_sum = ay_sum = az_sum = 0
        gx_sum = gy_sum = gz_sum = 0

        for _ in range(samples):
            ax, ay, az, gx, gy, gz = imu.read_raw()
            ax_sum += ax
            ay_sum += ay
            az_sum += az
            gx_sum += gx
            gy_sum += gy
            gz_sum += gz
            time.sleep(0.01)

        offsets = {
            "accel_offset": [ax_sum/samples, ay_sum/samples, az_sum/samples - 1.0],
            "gyro_offset": [gx_sum/samples, gy_sum/samples, gz_sum/samples],
        }

        print(f"Calibration complete: {offsets}")
        return {"success": True, "offsets": offsets}

    # Connect to server
    if not device.connect():
        print("Connection failed")
        return

    print("Publishing IMU data... (Ctrl+C to stop)")

    # Main loop
    last_publish = 0
    publish_interval_ms = 50  # 20 Hz

    try:
        while True:
            # Check for commands
            device._mqtt.check_msg()

            # Publish IMU data at interval
            now = time.ticks_ms()
            if time.ticks_diff(now, last_publish) >= publish_interval_ms:
                ax, ay, az, gx, gy, gz = imu.read_raw()

                # Convert gyro to rad/s
                import math
                gx_rad = gx * math.pi / 180
                gy_rad = gy * math.pi / 180
                gz_rad = gz * math.pi / 180

                imu_sensor.publish_raw(
                    accel=[ax * 9.81, ay * 9.81, az * 9.81],  # Convert to m/s^2
                    gyro=[gx_rad, gy_rad, gz_rad]
                )

                last_publish = now

            time.sleep_ms(5)

    except KeyboardInterrupt:
        pass
    finally:
        device.disconnect()
        print("Done")


if __name__ == "__main__":
    main()
