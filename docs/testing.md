# Testing Herd

## Quick Start

```bash
pip install httpx websockets
python scripts/test_device.py
```

This creates a **fake device** (`fake-device-01`) that sends synthetic sensor data to `herd.neevs.io`.

## What's Fake

| Component | Real | Fake |
|-----------|------|------|
| Server (herd.neevs.io) | Yes | - |
| Dashboard UI | Yes | - |
| API endpoints | Yes | - |
| Device (`fake-device-01`) | - | Yes |
| Sensor readings | - | Yes (random temperature/battery) |
| WebSocket connection | Yes | - |

## Options

```bash
# Custom device ID
python scripts/test_device.py --device-id my-test-bot

# Local server
python scripts/test_device.py --url http://localhost:8000
```

## Verify

1. Open https://herd.neevs.io
2. Run `python scripts/test_device.py`
3. Dashboard should show `fake-device-01` with live telemetry

## Cleanup

Stop the script (Ctrl+C). Fake devices disappear after heartbeat timeout (~6s).
