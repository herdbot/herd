# Testing Herd

## Local Testing (Zenoh)

Zenoh pub/sub requires direct TCP connection (port 7447), so run locally:

```bash
# Terminal 1: Start server
uvicorn server.api.main:app --port 8000

# Terminal 2: Run fake device
pip install eclipse-zenoh
python scripts/test_device.py
```

## What's Fake

| Component | Real | Fake |
|-----------|------|------|
| Server | Yes | - |
| Dashboard (localhost:8000) | Yes | - |
| Zenoh pub/sub | Yes | - |
| Device (`fake-device-01`) | - | Yes |
| Temperature readings | - | Yes (random 15-35°C) |

## Options

```bash
# Custom device ID
python scripts/test_device.py --device-id my-robot

# Custom Zenoh endpoint
python scripts/test_device.py --zenoh tcp/192.168.1.100:7447
```

## Topics

The fake device publishes to:
- `herd/devices/{id}/info` - Registration (DeviceInfo)
- `herd/devices/{id}/heartbeat` - Heartbeat every 2s
- `herd/sensors/{id}/temperature` - Temperature readings

## Cloud Testing

For herd.neevs.io, use the HTTP endpoints (Zenoh port not exposed):
- `POST /devices` - Register device
- `POST /devices/{id}/heartbeat` - Send heartbeat

## Cleanup

Devices go offline after ~6s without heartbeat.
