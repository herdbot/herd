# Testing Herd

## Quick Start

```bash
pip install httpx
python scripts/test_device.py
```

Creates a **fake device** that registers via HTTP API and sends heartbeats.

## What's Fake

| Component | Status |
|-----------|--------|
| Server (herd.neevs.io) | Real |
| Dashboard UI | Real |
| API endpoints | Real |
| `fake-device-01` | **FAKE** |
| Sensor readings | **FAKE** (random temperature) |
| Heartbeats | **FAKE** (simulated uptime) |

## Options

```bash
# Custom device ID
python scripts/test_device.py --device-id my-test-bot

# Local server
python scripts/test_device.py --url http://localhost:8000
```

## Verify

1. Run `python scripts/test_device.py`
2. Open https://herd.neevs.io
3. Dashboard shows `fake-device-01` as online

## Cleanup

Stop the script (Ctrl+C). Device goes offline after ~6s (heartbeat timeout).
