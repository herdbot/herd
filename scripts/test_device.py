#!/usr/bin/env python3
"""
Simulated device for testing herd server.

FAKE device that registers and sends telemetry via Zenoh pub/sub.
Requires server running locally (Zenoh port 7447 not exposed via Cloudflare).

Usage:
    # Terminal 1: Start server
    uvicorn server.api.main:app --port 8000

    # Terminal 2: Run fake device
    python scripts/test_device.py
"""

import argparse
import asyncio
import random
import signal
import sys
import time

try:
    import zenoh
except ImportError:
    print("Install zenoh: pip install eclipse-zenoh")
    sys.exit(1)

# Add parent to path for imports
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from shared.schemas import DeviceInfo, Heartbeat, SensorReading
from shared.schemas.messages import SensorType


class FakeDevice:
    """Simulated IoT device using Zenoh."""

    def __init__(self, zenoh_endpoint: str, device_id: str):
        self.zenoh_endpoint = zenoh_endpoint
        self.device_id = device_id
        self.session: zenoh.Session | None = None
        self.running = False
        self.start_time = time.time()
        self.temperature = 22.0

    def connect(self) -> bool:
        """Connect to Zenoh router."""
        try:
            config = zenoh.Config()
            config.insert_json5("mode", '"client"')
            config.insert_json5("connect/endpoints", f'["{self.zenoh_endpoint}"]')

            self.session = zenoh.open(config)
            print(f"[{self.device_id}] Connected to Zenoh at {self.zenoh_endpoint}")
            return True
        except Exception as e:
            print(f"[{self.device_id}] Zenoh connection failed: {e}")
            return False

    def register(self):
        """Publish device info to register."""
        if not self.session:
            return

        info = DeviceInfo(
            device_id=self.device_id,
            name=f"Fake Device ({self.device_id})",
            device_type="sensor_node",
        )

        topic = f"herd/devices/{self.device_id}/info"
        self.session.put(topic, info.to_msgpack())
        print(f"[{self.device_id}] Registered")

    def send_heartbeat(self):
        """Send heartbeat to stay online."""
        if not self.session:
            return

        uptime_ms = int((time.time() - self.start_time) * 1000)
        heartbeat = Heartbeat(
            device_id=self.device_id,
            uptime_ms=uptime_ms,
        )

        topic = f"herd/devices/{self.device_id}/heartbeat"
        self.session.put(topic, heartbeat.to_msgpack())

    def send_temperature(self):
        """Send fake temperature reading."""
        if not self.session:
            return

        self.temperature += random.uniform(-0.5, 0.5)
        self.temperature = max(15, min(35, self.temperature))

        reading = SensorReading(
            device_id=self.device_id,
            sensor_type=SensorType.TEMPERATURE,
            value=round(self.temperature, 2),
            unit="celsius",
        )

        topic = f"herd/sensors/{self.device_id}/temperature"
        self.session.put(topic, reading.to_msgpack())
        print(f"[{self.device_id}] temp={self.temperature:.1f}°C")

    def run(self):
        """Run the fake device."""
        if not self.connect():
            return

        self.register()
        self.running = True
        print(f"[{self.device_id}] Running (Ctrl+C to stop)")

        try:
            while self.running:
                self.send_heartbeat()
                self.send_temperature()
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            if self.session:
                self.session.close()
            print(f"\n[{self.device_id}] Stopped")

    def stop(self):
        """Stop the device."""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="Simulated herd device (Zenoh)")
    parser.add_argument(
        "--zenoh", default="tcp/localhost:7447", help="Zenoh endpoint"
    )
    parser.add_argument("--device-id", default="fake-device-01", help="Device ID")
    args = parser.parse_args()

    device = FakeDevice(args.zenoh, args.device_id)

    signal.signal(signal.SIGINT, lambda *_: device.stop())
    signal.signal(signal.SIGTERM, lambda *_: device.stop())

    device.run()


if __name__ == "__main__":
    main()
