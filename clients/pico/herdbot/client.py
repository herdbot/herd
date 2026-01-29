"""Main device client for herdbot (MicroPython/Pico W).

Handles MQTT connection, heartbeat, and command handling.
Same API as ESP32 client for compatibility.
"""

import time
import json

try:
    from umqtt.simple import MQTTClient
    import machine
except ImportError:
    MQTTClient = None
    machine = None


class Device:
    """Herdbot device client for Pico W."""

    def __init__(
        self,
        device_id: str,
        device_type: str,
        server: str = None,
        port: int = 1883,
        name: str = None,
        capabilities: list = None,
        firmware_version: str = "0.1.0",
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.server = server
        self.port = port
        self.name = name or device_id
        self.capabilities = capabilities or []
        self.firmware_version = firmware_version

        self._mqtt = None
        self._connected = False
        self._command_handlers = {}
        self._heartbeat_sequence = 0
        self._start_time = time.ticks_ms() if hasattr(time, 'ticks_ms') else int(time.time() * 1000)
        self._topic_prefix = "herd"
        self._sensors = {}

    def connect(self) -> bool:
        """Connect to the MQTT broker."""
        if MQTTClient is None:
            print("MQTT not available")
            return False

        if not self.server:
            # Try discovery
            print("No server specified, discovery not implemented for Pico")
            return False

        try:
            self._mqtt = MQTTClient(
                self.device_id,
                self.server,
                port=self.port,
                keepalive=60,
            )

            self._mqtt.set_callback(self._on_message)
            self._mqtt.connect()
            self._connected = True

            cmd_topic = f"{self._topic_prefix}/commands/{self.device_id}"
            self._mqtt.subscribe(cmd_topic.encode())

            self._publish_device_info()
            print(f"Connected to {self.server}:{self.port}")
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from broker."""
        if self._mqtt and self._connected:
            self._mqtt.disconnect()
            self._connected = False

    def _publish_device_info(self):
        """Publish device info."""
        info = {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "name": self.name,
            "capabilities": self.capabilities,
            "firmware_version": self.firmware_version,
            "timestamp": self._get_timestamp(),
        }
        topic = f"{self._topic_prefix}/devices/{self.device_id}/info"
        self._publish(topic, info)

    def _publish_heartbeat(self):
        """Publish heartbeat."""
        self._heartbeat_sequence += 1
        heartbeat = {
            "device_id": self.device_id,
            "sequence": self._heartbeat_sequence,
            "uptime_ms": self._get_uptime_ms(),
            "load": 0.0,
            "memory_free": self._get_free_memory(),
            "timestamp": self._get_timestamp(),
        }
        topic = f"{self._topic_prefix}/devices/{self.device_id}/heartbeat"
        self._publish(topic, heartbeat)

    def _publish(self, topic: str, data: dict):
        """Publish JSON data."""
        if self._mqtt and self._connected:
            payload = json.dumps(data)
            self._mqtt.publish(topic.encode(), payload.encode())

    def publish_sensor(self, sensor_id: str, sensor_type: str, value, unit: str = ""):
        """Publish sensor reading."""
        reading = {
            "device_id": self.device_id,
            "sensor_type": sensor_type,
            "sensor_id": sensor_id,
            "value": value,
            "unit": unit,
            "quality": 1.0,
            "timestamp": self._get_timestamp(),
        }
        topic = f"{self._topic_prefix}/sensors/{self.device_id}/{sensor_id}"
        self._publish(topic, reading)

    def on_command(self, action: str):
        """Decorator for command handlers."""
        def decorator(func):
            self._command_handlers[action] = func
            return func
        return decorator

    def _on_message(self, topic, msg):
        """Handle incoming messages."""
        try:
            topic_str = topic.decode() if isinstance(topic, bytes) else topic
            data = json.loads(msg.decode() if isinstance(msg, bytes) else msg)

            if "/commands/" in topic_str:
                self._handle_command(data)
        except Exception as e:
            print(f"Message error: {e}")

    def _handle_command(self, data: dict):
        """Handle command."""
        action = data.get("action")
        params = data.get("params", {})
        request_id = data.get("request_id")

        if action in self._command_handlers:
            try:
                result = self._command_handlers[action](params)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
        else:
            result = None
            success = False
            error = f"Unknown action: {action}"

        response = {
            "request_id": request_id,
            "success": success,
            "result": result,
            "error": error,
            "timestamp": self._get_timestamp(),
        }
        topic = f"{self._topic_prefix}/commands/{self.device_id}/response"
        self._publish(topic, response)

    def run(self, heartbeat_interval_ms: int = 2000):
        """Run main loop."""
        if not self._connected:
            if not self.connect():
                return

        last_heartbeat = 0
        print(f"Device {self.device_id} running...")

        try:
            while True:
                if self._mqtt:
                    self._mqtt.check_msg()

                now = self._get_uptime_ms()
                if now - last_heartbeat >= heartbeat_interval_ms:
                    self._publish_heartbeat()
                    last_heartbeat = now

                time.sleep_ms(10) if hasattr(time, 'sleep_ms') else time.sleep(0.01)

        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()

    def _get_timestamp(self) -> str:
        t = time.localtime()
        return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}T{t[3]:02d}:{t[4]:02d}:{t[5]:02d}Z"

    def _get_uptime_ms(self) -> int:
        if hasattr(time, 'ticks_ms'):
            return time.ticks_diff(time.ticks_ms(), self._start_time)
        return int((time.time() * 1000) - self._start_time)

    def _get_free_memory(self) -> int:
        try:
            import gc
            gc.collect()
            return gc.mem_free()
        except:
            return 0
