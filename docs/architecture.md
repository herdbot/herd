# Herdbot Architecture

## Overview

Herdbot is designed as a lightweight, modular robotics framework that bridges the gap between simple maker projects and full ROS deployments.

## Core Principles

1. **Simplicity** - Easy to understand and modify
2. **Modularity** - Components can be used independently
3. **Scalability** - Works for one device or many
4. **Educational** - Well-documented and approachable

## Components

### Zenoh Hub

The Zenoh Hub is the messaging backbone:

```
┌─────────────────────────────────────────┐
│              Zenoh Session              │
├─────────────────────────────────────────┤
│  Topics:                                │
│    herd/devices/{id}/info      ← Registration
│    herd/devices/{id}/heartbeat ← Presence
│    herd/sensors/{id}/{sensor}  ← Telemetry
│    herd/commands/{id}          → Commands
│    herd/commands/{id}/response ← Responses
│    herd/ai/detections          ← AI outputs
└─────────────────────────────────────────┘
```

### Device Registry

Tracks all connected devices:

- Device information (type, capabilities)
- Connection status (online/offline)
- Heartbeat monitoring
- Online/offline event callbacks

### API Layer

FastAPI-based REST and WebSocket interface:

- **REST** - CRUD operations, commands
- **WebSocket** - Real-time telemetry streaming
- **Static Files** - Web dashboard

### MQTT Bridge

For ESP32/Pico devices that can't use Zenoh directly:

```
ESP32 ──MQTT──> Bridge ──Zenoh──> Hub
```

### AI Integration

Pluggable AI providers:

```python
class AIProvider(ABC):
    async def interpret(self, data, prompt) -> str
    async def plan(self, goal, context) -> list[Command]
    async def chat(self, message, history) -> str
```

### Visualization

- **Rerun Bridge** - 3D visualization, time series
- **Web Dashboard** - Browser-based monitoring

## Message Flow

### Sensor Data Flow

```
ESP32 Sensor
    │
    │ MQTT: herd/sensors/esp32-01/temperature
    ▼
MQTT Bridge
    │
    │ Zenoh: herd/sensors/esp32-01/temperature
    ▼
Zenoh Hub
    │
    ├──> Device Registry (update last_seen)
    ├──> Rerun Bridge (visualization)
    ├──> AI Agent (trigger check)
    └──> WebSocket (stream to clients)
```

### Command Flow

```
Web Dashboard
    │
    │ POST /devices/robot-01/command
    ▼
FastAPI
    │
    │ Zenoh: herd/commands/robot-01
    ▼
Zenoh Hub
    │
    │ MQTT: herd/commands/robot-01
    ▼
MQTT Bridge
    │
    ▼
Robot ESP32
    │
    │ MQTT: herd/commands/robot-01/response
    ▼
(response flows back)
```

## Data Schemas

All messages use Pydantic models with MessagePack serialization:

```python
class SensorReading(MessageBase):
    device_id: str
    sensor_type: SensorType
    value: float | list | dict
    unit: str
    timestamp: datetime

class Command(MessageBase):
    device_id: str
    action: str
    params: dict
    request_id: UUID
    timeout_ms: int
```

## Deployment Modes

### Local Development

```bash
herdbot start --reload
```

### Docker

```bash
docker-compose up
```

### GitHub Actions (Cloud)

Long-running workflow with auto-restart:

- Runs for 5.5 hours
- Triggers new workflow before timeout
- Cloudflare Tunnel for external access

## Extension Points

### Custom Sensors

```python
class MySensor(Sensor):
    def __init__(self, device, sensor_id):
        super().__init__(device, sensor_id, sensor_type="custom")

    def publish_custom(self, data):
        self.publish({"custom_field": data})
```

### Custom AI Triggers

```python
from server.ai.agent import Trigger

def my_condition(ctx):
    return ctx["value"] > 100

trigger = Trigger(
    name="high_value",
    condition=my_condition,
    prompt="Value exceeded 100. Analyze.",
)
```

### Custom API Routes

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/custom")
async def custom_endpoint():
    return {"custom": "data"}

# Add to app in server/api/main.py
```
