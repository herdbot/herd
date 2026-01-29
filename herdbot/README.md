# Herdbot 🤖

A lightweight, educational robotics framework bridging the gap between simple Raspberry Pi projects and full ROS stacks. Uses Zenoh for messaging, supports ESP32/Pico clients, and integrates easily with cloud AI services.

## Features

- **Zenoh Messaging** - High-performance pub/sub with automatic discovery
- **ESP32/Pico Support** - MicroPython client libraries for embedded devices
- **REST API** - FastAPI-based HTTP and WebSocket interface
- **AI Integration** - OpenAI and Anthropic providers for intelligent automation
- **Visualization** - Rerun integration and web dashboard
- **GitHub Actions Deployment** - Run as a long-running cloud service

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/herdbot.git
cd herdbot

# Install dependencies
pip install -e .

# Start the server
herdbot start
```

### Connect an ESP32

```python
from herdbot import Device, Sensor

device = Device(
    device_id="sensor-01",
    device_type="sensor_node",
    server="192.168.1.100"
)

temp = Sensor(device, "temp", sensor_type="temperature", unit="C")

while True:
    reading = read_temperature()  # Your sensor code
    temp.publish(reading)
    time.sleep(1)
```

### Send Commands

```bash
# List devices
herdbot devices

# Send a command
herdbot send robot-01 move --params '{"linear": 0.5, "angular": 0}'

# Monitor telemetry
herdbot monitor sensor-01
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Herdbot Server                          │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│   Zenoh     │   FastAPI   │   Rerun     │   AI Providers   │
│   Hub       │   REST/WS   │   Bridge    │   OpenAI/Claude  │
└──────┬──────┴──────┬──────┴──────┬──────┴────────┬─────────┘
       │             │             │               │
       │ Zenoh/MQTT  │ HTTP/WS     │ Rerun SDK     │ API
       │             │             │               │
┌──────┴──────┐  ┌───┴────┐  ┌────┴─────┐  ┌─────┴─────┐
│  ESP32/Pico │  │  Web   │  │  Rerun   │  │  OpenAI   │
│  Devices    │  │ Browser│  │  Viewer  │  │  Claude   │
└─────────────┘  └────────┘  └──────────┘  └───────────┘
```

## Configuration

Environment variables (or `.env` file):

```bash
# Server
HERDBOT_API_PORT=8000
HERDBOT_SERVER_ID=herdbot-01

# Zenoh
HERDBOT_ZENOH_MODE=peer
HERDBOT_ZENOH_LISTEN=["tcp/0.0.0.0:7447"]

# MQTT Bridge (for ESP32/Pico)
HERDBOT_MQTT_ENABLED=true
HERDBOT_MQTT_PORT=1883

# AI (optional)
HERDBOT_OPENAI_API_KEY=sk-...
HERDBOT_ANTHROPIC_API_KEY=sk-ant-...
HERDBOT_DEFAULT_AI_PROVIDER=openai
```

## API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices` | GET | List all devices |
| `/devices/{id}` | GET | Get device details |
| `/devices/{id}/command` | POST | Send command |
| `/devices/{id}/status` | GET | Get device status |
| `/telemetry/stream/{id}` | WS | Stream telemetry |
| `/telemetry/stream/all` | WS | Stream all telemetry |
| `/ai/interpret` | POST | AI data interpretation |
| `/ai/plan` | POST | AI action planning |
| `/ai/chat` | POST | AI chat interface |
| `/health` | GET | Health check |

### Message Types

```python
# Sensor reading
SensorReading(
    device_id="sensor-01",
    sensor_type="temperature",
    value=23.5,
    unit="C"
)

# Command
Command(
    device_id="robot-01",
    action="move",
    params={"linear": 0.5, "angular": 0}
)

# Pose
Pose2D(x=1.0, y=2.0, theta=0.5, frame_id="world")
```

## GitHub Actions Deployment

Herdbot can run as a long-running GitHub Actions workflow with automatic restart:

```yaml
# See .github/workflows/herdbot.yml
```

Features:
- Runs for ~5.5 hours (below 6-hour limit)
- Auto-triggers new workflow before timeout
- Parallel instances for zero-downtime restarts
- Cloudflare Tunnel for external access

## Project Structure

```
herdbot/
├── server/
│   ├── core/          # Zenoh hub, device registry
│   ├── api/           # FastAPI routes
│   ├── viz/           # Rerun bridge
│   ├── ai/            # AI providers
│   └── dashboard/     # Web UI
├── clients/
│   ├── esp32/         # ESP32 MicroPython library
│   └── pico/          # Pico W MicroPython library
├── shared/
│   └── schemas/       # Message definitions
├── cli/               # CLI tool
├── docs/              # Documentation
└── examples/          # Example projects
```

## Examples

See the `examples/` directory:

1. **01-blink-led** - Simplest possible example
2. **02-sensor-dashboard** - ESP32 + web visualization
3. **03-ai-object-detector** - Camera + AI integration
4. **04-multi-robot** - Multiple device coordination

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read the contributing guidelines first.
