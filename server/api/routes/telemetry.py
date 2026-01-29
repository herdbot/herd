"""Telemetry streaming API routes with WebSocket support."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import structlog

from shared.schemas import SensorReading

logger = structlog.get_logger()

router = APIRouter()


class TelemetryStats(BaseModel):
    """Telemetry statistics."""

    total_messages: int
    messages_per_second: float
    active_streams: int
    devices_streaming: list[str]


# Active WebSocket connections
_active_connections: dict[str, list[WebSocket]] = {}
_all_connections: list[WebSocket] = []
_message_count = 0
_last_count_reset = 0.0


async def broadcast_sensor_data(device_id: str, data: SensorReading) -> None:
    """Broadcast sensor data to connected WebSocket clients.

    Args:
        device_id: Source device ID
        data: Sensor reading to broadcast
    """
    global _message_count
    _message_count += 1

    message = data.model_dump_json()

    # Send to device-specific subscribers
    if device_id in _active_connections:
        for ws in _active_connections[device_id]:
            try:
                await ws.send_text(message)
            except Exception:
                pass

    # Send to all-stream subscribers
    for ws in _all_connections:
        try:
            await ws.send_text(message)
        except Exception:
            pass


@router.websocket("/stream/{device_id}")
async def device_stream(websocket: WebSocket, device_id: str) -> None:
    """WebSocket endpoint for streaming a specific device's telemetry."""
    await websocket.accept()

    # Add to connections
    if device_id not in _active_connections:
        _active_connections[device_id] = []
    _active_connections[device_id].append(websocket)

    logger.info("websocket_connected", device_id=device_id)

    try:
        while True:
            # Keep connection alive, handle client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle ping/pong or commands from client
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text(json.dumps({"type": "keepalive"}))

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", device_id=device_id)
    finally:
        if device_id in _active_connections:
            _active_connections[device_id].remove(websocket)
            if not _active_connections[device_id]:
                del _active_connections[device_id]


@router.websocket("/stream/all")
async def all_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming all device telemetry."""
    await websocket.accept()

    _all_connections.append(websocket)
    logger.info("websocket_all_connected")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "keepalive"}))

    except WebSocketDisconnect:
        logger.info("websocket_all_disconnected")
    finally:
        _all_connections.remove(websocket)


@router.get("/stats", response_model=TelemetryStats)
async def get_telemetry_stats() -> TelemetryStats:
    """Get telemetry streaming statistics."""
    import time

    global _last_count_reset, _message_count

    now = time.time()
    elapsed = now - _last_count_reset if _last_count_reset > 0 else 1.0
    mps = _message_count / elapsed if elapsed > 0 else 0

    # Reset counter periodically
    if elapsed > 60:
        _message_count = 0
        _last_count_reset = now

    return TelemetryStats(
        total_messages=_message_count,
        messages_per_second=round(mps, 2),
        active_streams=len(_all_connections) + sum(len(v) for v in _active_connections.values()),
        devices_streaming=list(_active_connections.keys()),
    )


@router.get("/latest/{device_id}")
async def get_latest_telemetry(device_id: str) -> dict[str, Any]:
    """Get the latest telemetry data for a device.

    Note: This queries the Zenoh network for the latest stored values.
    """
    from server.api.main import get_zenoh_hub
    from server.core import get_settings

    hub = get_zenoh_hub()
    settings = get_settings()

    # Query for latest sensor data
    selector = f"{settings.topic_sensors}/{device_id}/**"
    results = await hub.query(selector, timeout_s=2.0)

    readings = []
    for key, payload in results:
        try:
            reading = SensorReading.from_msgpack(payload)
            readings.append(reading.model_dump(mode="json"))
        except Exception:
            pass

    return {
        "device_id": device_id,
        "readings": readings,
        "count": len(readings),
    }
