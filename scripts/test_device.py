#!/usr/bin/env python3
"""
Simulated device for testing herd.neevs.io

This creates a FAKE device that:
- Registers with the server
- Sends simulated sensor data (temperature, battery)
- Responds to commands

Usage:
    python scripts/test_device.py [--url URL] [--device-id ID]

Default connects to herd.neevs.io. All data is synthetic.
"""

import argparse
import asyncio
import json
import random
import signal
import sys
from datetime import datetime

try:
    import httpx
    import websockets
except ImportError:
    print("Install dependencies: pip install httpx websockets")
    sys.exit(1)


class FakeDevice:
    """Simulated IoT device for testing."""

    def __init__(self, base_url: str, device_id: str):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        self.running = False
        self.temperature = 22.0  # Starting temp

    async def register(self) -> bool:
        """Register device with server."""
        async with httpx.AsyncClient() as client:
            try:
                # Check server health
                resp = await client.get(f"{self.base_url}/health")
                if resp.status_code != 200:
                    print(f"Server unhealthy: {resp.status_code}")
                    return False
                print(f"[{self.device_id}] Connected to {self.base_url}")
                return True
            except Exception as e:
                print(f"Connection failed: {e}")
                return False

    async def send_telemetry(self):
        """Send fake sensor data via WebSocket."""
        uri = f"{self.ws_url}/telemetry/stream/all"
        print(f"[{self.device_id}] Streaming to {uri}")

        try:
            async with websockets.connect(uri) as ws:
                while self.running:
                    # Simulate temperature drift
                    self.temperature += random.uniform(-0.5, 0.5)
                    self.temperature = max(15, min(35, self.temperature))

                    # Send temperature reading
                    await ws.send(json.dumps({
                        "type": "sensor",
                        "device_id": self.device_id,
                        "sensor_type": "temperature",
                        "value": round(self.temperature, 2),
                        "unit": "celsius",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

                    # Send battery level
                    await ws.send(json.dumps({
                        "type": "sensor",
                        "device_id": self.device_id,
                        "sensor_type": "battery",
                        "value": random.randint(70, 100),
                        "unit": "percent",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

                    print(f"[{self.device_id}] temp={self.temperature:.1f}°C")
                    await asyncio.sleep(2)

        except websockets.exceptions.ConnectionClosed:
            print(f"[{self.device_id}] Connection closed")
        except Exception as e:
            print(f"[{self.device_id}] Error: {e}")

    async def run(self):
        """Run the fake device."""
        if not await self.register():
            return

        self.running = True
        print(f"[{self.device_id}] Sending fake telemetry (Ctrl+C to stop)")
        await self.send_telemetry()

    def stop(self):
        """Stop the device."""
        self.running = False
        print(f"\n[{self.device_id}] Stopped")


async def main():
    parser = argparse.ArgumentParser(description="Simulated herd device")
    parser.add_argument("--url", default="https://herd.neevs.io", help="Server URL")
    parser.add_argument("--device-id", default="fake-device-01", help="Device ID")
    args = parser.parse_args()

    device = FakeDevice(args.url, args.device_id)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, device.stop)

    await device.run()


if __name__ == "__main__":
    asyncio.run(main())
