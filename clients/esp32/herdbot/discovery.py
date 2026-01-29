"""Server discovery for herdbot (MicroPython/ESP32).

Supports mDNS discovery and manual configuration.
"""

import time

try:
    import network
    import socket
except ImportError:
    network = None
    socket = None


# Default server port
DEFAULT_PORT = 1883

# mDNS service name
MDNS_SERVICE = "_herdbot._tcp.local"


def discover_server(timeout_s: int = 5) -> str:
    """Discover herdbot server on the local network.

    Attempts mDNS discovery first, then falls back to
    broadcast discovery.

    Args:
        timeout_s: Discovery timeout in seconds

    Returns:
        Server IP address or None if not found
    """
    # Try mDNS first
    server = _discover_mdns(timeout_s)
    if server:
        return server

    # Fallback to UDP broadcast
    server = _discover_broadcast(timeout_s)
    if server:
        return server

    return None


def _discover_mdns(timeout_s: int) -> str:
    """Discover server via mDNS.

    Note: MicroPython mDNS support varies by platform.
    """
    try:
        # Try to resolve mDNS name
        # This is platform-specific and may not work on all ESP32 builds
        import mdns

        mdns.init()
        results = mdns.query(MDNS_SERVICE, timeout_s * 1000)

        if results:
            return results[0].address

    except (ImportError, AttributeError):
        # mDNS not available
        pass
    except Exception as e:
        print(f"mDNS discovery error: {e}")

    return None


def _discover_broadcast(timeout_s: int) -> str:
    """Discover server via UDP broadcast.

    Sends a discovery request and waits for server response.
    """
    if socket is None:
        return None

    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(1)

        # Broadcast discovery request
        discovery_msg = b'{"type": "herdbot_discover"}'
        broadcast_addr = "255.255.255.255"
        discovery_port = 7448

        start_time = time.time()

        while time.time() - start_time < timeout_s:
            try:
                sock.sendto(discovery_msg, (broadcast_addr, discovery_port))

                # Wait for response
                try:
                    data, addr = sock.recvfrom(1024)

                    # Parse response
                    import json
                    response = json.loads(data.decode())

                    if response.get("type") == "herdbot_server":
                        sock.close()
                        return addr[0]

                except socket.timeout:
                    pass

            except Exception as e:
                print(f"Broadcast error: {e}")

            time.sleep(0.5)

        sock.close()

    except Exception as e:
        print(f"Discovery error: {e}")

    return None


def get_local_ip() -> str:
    """Get the local IP address of this device.

    Returns:
        Local IP address or "0.0.0.0" if not connected
    """
    if network is None:
        return "0.0.0.0"

    try:
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            return wlan.ifconfig()[0]
    except:
        pass

    return "0.0.0.0"


def wait_for_wifi(ssid: str = None, password: str = None, timeout_s: int = 30) -> bool:
    """Wait for WiFi connection.

    If ssid/password provided, attempts to connect.
    Otherwise, waits for existing connection.

    Args:
        ssid: WiFi network name (optional)
        password: WiFi password (optional)
        timeout_s: Connection timeout

    Returns:
        True if connected
    """
    if network is None:
        print("Network module not available")
        return False

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if ssid:
        print(f"Connecting to {ssid}...")
        wlan.connect(ssid, password)

    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout_s:
            print("WiFi connection timeout")
            return False
        time.sleep(0.5)

    ip = wlan.ifconfig()[0]
    print(f"Connected: {ip}")
    return True
