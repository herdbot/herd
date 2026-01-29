#!/usr/bin/env python3
"""
Simulated device for testing herd.neevs.io

This creates a FAKE device that:
- Registers with the server via HTTP API
- Sends heartbeats to stay online
- Simulates temperature sensor

Usage:
    python scripts/test_device.py [--url URL] [--device-id ID]

Default connects to herd.neevs.io. All data is synthetic.
"""

import argparse
import asyncio
import random
import signal
import sys

try:
    import httpx
except ImportError:
    print("Install: pip install httpx")
    sys.exit(1)


class FakeDevice:
    """Simulated IoT device for testing."""

    def __init__(self, base_url: str, device_id: str):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.running = False
        self.temperature = 22.0
        self.uptime_ms = 0
        self.sequence = 0

    async def register(self) -> bool:
        """Register device with server."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/devices",
                    json={
                        "device_id": self.device_id,
                        "device_type": "sensor_node",
                        "name": f"Fake Device ({self.device_id})",
                        "capabilities": [
                            {"name": "temperature", "capability_type": "sensor"},
                            {"name": "battery", "capability_type": "sensor"},
                        ],
                        "firmware_version": "0.1.0-fake",
                    },
                )
                if resp.status_code in (200, 201):
                    print(f"[{self.device_id}] Registered")
                    return True
                print(f"[{self.device_id}] Registration failed: {resp.status_code} {resp.text}")
                return False
            except Exception as e:
                print(f"[{self.device_id}] Connection failed: {e}")
                return False

    async def send_heartbeat(self, client: httpx.AsyncClient) -> bool:
        """Send heartbeat to stay online."""
        try:
            self.sequence += 1
            self.uptime_ms += 2000
            resp = await client.post(
                f"{self.base_url}/devices/{self.device_id}/heartbeat",
                json={
                    "device_id": self.device_id,
                    "sequence": self.sequence,
                    "uptime_ms": self.uptime_ms,
                    "load": random.uniform(0.1, 0.4),
                    "memory_free": random.randint(50000, 100000),
                },
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def send_telemetry(self, client: httpx.AsyncClient) -> bool:
        """Send sensor telemetry."""
        try:
            # Temperature
            await client.post(
                f"{self.base_url}/telemetry/publish",
                json={
                    "device_id": self.device_id,
                    "sensor_type": "temperature",
                    "value": round(self.temperature, 2),
                    "unit": "celsius",
                },
            )
            # Battery
            await client.post(
                f"{self.base_url}/telemetry/publish",
                json={
                    "device_id": self.device_id,
                    "sensor_type": "battery",
                    "value": random.randint(70, 100),
                    "unit": "percent",
                },
            )
            return True
        except Exception:
            return False

    async def run(self):
        """Run the fake device."""
        if not await self.register():
            return

        self.running = True
        print(f"[{self.device_id}] Running (Ctrl+C to stop)")

        async with httpx.AsyncClient() as client:
            while self.running:
                self.temperature += random.uniform(-0.5, 0.5)
                self.temperature = max(15, min(35, self.temperature))

                hb_ok = await self.send_heartbeat(client)
                tel_ok = await self.send_telemetry(client)

                if hb_ok and tel_ok:
                    print(f"[{self.device_id}] temp={self.temperature:.1f}°C uptime={self.uptime_ms // 1000}s")
                else:
                    print(f"[{self.device_id}] failed (hb={hb_ok} tel={tel_ok})")

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
