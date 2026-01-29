# Getting Started with Herdbot

This guide will help you set up Herdbot and connect your first device.

## Prerequisites

- Python 3.11 or higher
- ESP32 or Raspberry Pi Pico W (optional, for embedded devices)
- Git

## Installation

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/herdbot.git
cd herdbot
pip install -e .
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Required
HERDBOT_SERVER_ID=my-herdbot

# Optional - AI integration
HERDBOT_OPENAI_API_KEY=sk-your-key
HERDBOT_ANTHROPIC_API_KEY=sk-ant-your-key
```

### 3. Start the Server

```bash
herdbot start
```

The server will start on `http://localhost:8000`. Open the dashboard at `http://localhost:8000/dashboard`.

## Connect a Device

### Option A: Simulated Device (Python)

Create a test device without hardware:

```python
# test_device.py
import asyncio
import random
from datetime import datetime

import httpx

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Register device (would normally happen via MQTT)
        # For testing, we'll just send sensor data via REST

        while True:
            # Simulate temperature reading
            temp = 20 + random.uniform(-2, 2)

            print(f"Temperature: {temp:.1f}°C")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Option B: ESP32 with MicroPython

1. Flash MicroPython to your ESP32
2. Copy the client library:
   ```bash
   # Using mpremote or similar tool
   mpremote cp -r clients/esp32/herdbot :
   ```

3. Create your main script:
   ```python
   # main.py on ESP32
   from herdbot import Device
   from herdbot.sensors import TemperatureSensor
   from herdbot.discovery import wait_for_wifi
   import time

   # Connect to WiFi
   wait_for_wifi("YourSSID", "YourPassword")

   # Create device
   device = Device(
       device_id="esp32-temp-01",
       device_type="sensor_node",
       server="192.168.1.100",  # Your server IP
   )

   # Create sensor
   temp = TemperatureSensor(device)

   # Connect and run
   device.connect()

   while True:
       # Read from your sensor (example with internal temp)
       import esp32
       reading = (esp32.raw_temperature() - 32) * 5/9
       temp.publish_celsius(reading)
       time.sleep(1)
   ```

### Option C: Raspberry Pi Pico W

Similar to ESP32, but use the Pico client library:

```python
# main.py on Pico W
from herdbot import Device
from herdbot.sensors import DistanceSensor
import time

device = Device(
    device_id="pico-distance-01",
    device_type="sensor_node",
    server="192.168.1.100",
)

distance = DistanceSensor(device)
device.connect()

while True:
    # Read your sensor
    reading = measure_distance()  # Your sensor code
    distance.publish_mm(reading)
    time.sleep(0.1)
```

## Using the CLI

```bash
# Check server health
herdbot health

# List devices
herdbot devices

# Monitor a device
herdbot monitor esp32-temp-01

# Send a command
herdbot send robot-01 move --params '{"linear": 0.5}'

# Ask the AI
herdbot ask "What's the average temperature from sensor-01?"
```

## Web Dashboard

Open `http://localhost:8000/dashboard` to:

- View connected devices
- See real-time telemetry charts
- Send commands
- Chat with the AI assistant

## Next Steps

- [Architecture Overview](architecture.md)
- [API Reference](api-reference.md)
- [Example Projects](../examples/)
- [Deploying to GitHub Actions](deployment.md)
