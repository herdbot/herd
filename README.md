# Herdbot

A lightweight robotics framework bridging simple Pi projects and full ROS stacks. Built on [Zenoh](https://zenoh.io/) for efficient pub/sub messaging, with support for ESP32/Pico microcontrollers and cloud AI integration.

## Features

- **Zenoh-based messaging**: Efficient, low-latency pub/sub communication
- **Device management**: Automatic discovery and heartbeat monitoring
- **Multi-platform clients**: MicroPython libraries for ESP32 and Raspberry Pi Pico
- **AI integration**: OpenAI and Anthropic providers for intelligent robotics
- **REST/WebSocket API**: FastAPI-based interface for web dashboards
- **Visualization**: Rerun SDK integration for 3D visualization
- **GitHub Actions deployment**: Run as a long-running workflow with Cloudflare Tunnel

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/jonasnvs/herdbot.git
cd herdbot

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
```

### Running the Server

```bash
# Start with CLI
herdbot server --host 0.0.0.0 --port 8080

# Or with uvicorn directly
uvicorn server.api.app:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
# Build and run
docker build -t herdbot .
docker run -p 8080:8080 --env-file .env herdbot
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Herdbot Server                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Zenoh Hub  │  │  Device     │  │  REST/WebSocket API │  │
│  │  (pub/sub)  │  │  Registry   │  │  (FastAPI)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  AI Service │  │  Rerun      │  │  MQTT Bridge        │  │
│  │  (LLM)      │  │  (Viz)      │  │  (ESP32/Pico)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                                      │
         │ Zenoh                                │ MQTT
         ▼                                      ▼
┌─────────────────┐                  ┌─────────────────┐
│  Native Client  │                  │  ESP32 / Pico   │
│  (Python/Rust)  │                  │  (MicroPython)  │
└─────────────────┘                  └─────────────────┘
```

## Configuration

Environment variables (`.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `HERDBOT_HOST` | Server host | `0.0.0.0` |
| `HERDBOT_PORT` | Server port | `8080` |
| `HERDBOT_ZENOH_CONNECT` | Zenoh router address | (peer mode) |
| `HERDBOT_MQTT_BROKER` | MQTT broker for ESP32/Pico | `localhost` |
| `HERDBOT_MQTT_PORT` | MQTT port | `1883` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare tunnel token | - |

## Client Libraries

### ESP32 (MicroPython)

```python
from herdbot_client import HerdClient

client = HerdClient(
    device_id="esp32-001",
    mqtt_broker="your-server.com"
)
client.connect()

# Publish sensor data
client.publish_sensor("temperature", 25.5)

# Subscribe to commands
def on_command(cmd):
    print(f"Received: {cmd}")

client.on_command = on_command
```

### Raspberry Pi Pico

```python
from herdbot_pico import HerdClient

client = HerdClient(
    device_id="pico-001",
    wifi_ssid="YourNetwork",
    wifi_password="password",
    mqtt_broker="your-server.com"
)
client.connect()
```

## GitHub Actions Deployment

Herdbot can run as a GitHub Actions workflow with automatic restart to handle the 6-hour timeout limit:

1. Fork this repository
2. Add secrets in repository settings:
   - `OPENAI_API_KEY` (optional)
   - `ANTHROPIC_API_KEY` (optional)
   - `CLOUDFLARE_TUNNEL_TOKEN` (optional, for external access)
3. Enable the workflow in Actions tab
4. Trigger manually or on push

The workflow runs for 5.5 hours then triggers a new instance before timeout.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/devices` | GET | List all devices |
| `/api/devices/{id}` | GET | Get device details |
| `/api/devices/{id}/command` | POST | Send command to device |
| `/api/ai/chat` | POST | Chat with AI assistant |
| `/ws` | WebSocket | Real-time updates |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy server shared

# Run tests
pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.
