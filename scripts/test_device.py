#!/usr/bin/env python3
"""
Simulated device for testing herd.neevs.io

This creates a FAKE device that:
- Registers with the server via HTTP
- Sends heartbeats to stay online

Usage:
    python scripts/test_device.py [--url URL] [--device-id ID]

Default connects to herd.neevs.io. All data is synthetic.
"""

import argparse
import asyncio
import signal
import sys

try:
    import httpx
except ImportError:
    print("Install dependencies: pip install httpx")
    sys.exit(1)


class FakeDevice:
    """Simulated IoT device for testing."""

    def __init__(self, base_url: str, device_id: str):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.running = False

    async def register(self) -> bool:
        """Register device with server."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/devices",
                    json={
                        "device_id": self.device_id,
                        "name": f"Fake Device ({self.device_id})",
                        "device_type": "sensor_node",
                    },
                )
                if resp.status_code in (200, 201):
                    print(f"[{self.device_id}] Registered with {self.base_url}")
                    return True
                else:
                    print(f"[{self.device_id}] Registration failed: {resp.status_code} {resp.text}")
                    return False
            except Exception as e:
                print(f"[{self.device_id}] Connection failed: {e}")
                return False

    async def run(self):
        """Run the fake device."""
        if not await self.register():
            return

        self.running = True
        print(f"[{self.device_id}] Sending heartbeats (Ctrl+C to stop)")

        async with httpx.AsyncClient() as client:
            while self.running:
                try:
                    resp = await client.post(f"{self.base_url}/devices/{self.device_id}/heartbeat")
                    if resp.status_code == 200:
                        print(f"[{self.device_id}] heartbeat ok")
                    else:
                        print(f"[{self.device_id}] heartbeat failed: {resp.status_code}")
                except Exception as e:
                    print(f"[{self.device_id}] heartbeat error: {e}")
                await asyncio.sleep(2)

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
