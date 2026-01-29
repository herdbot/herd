# Example 01: Blink LED

The simplest possible herdbot example. Blinks an LED and reports state to the server.

## What You'll Learn

- Basic device setup
- Command handling
- Sensor publishing

## Hardware Required

- ESP32 or Raspberry Pi Pico W
- LED connected to GPIO 2 (or use built-in LED)

## Setup

1. Start the herdbot server:
   ```bash
   herdbot start
   ```

2. Update the configuration in `main.py`:
   - Set `SERVER_IP` to your server's IP address
   - Adjust `LED_PIN` if needed

3. Upload to your device using mpremote or similar:
   ```bash
   mpremote cp main.py :main.py
   mpremote run main.py
   ```

## Commands

You can send these commands via the dashboard or CLI:

```bash
# Turn LED on
herdbot send blink-led-01 set_led --params '{"state": true}'

# Turn LED off
herdbot send blink-led-01 set_led --params '{"state": false}'

# Toggle LED
herdbot send blink-led-01 toggle

# Change blink interval
herdbot send blink-led-01 set_blink --params '{"enabled": true, "interval": 0.5}'

# Stop blinking
herdbot send blink-led-01 set_blink --params '{"enabled": false}'
```

## Simulation Mode

You can run this example without hardware by running it on your computer:

```bash
cd examples/01-blink-led
python main.py
```

The LED state will be printed to the console.
