"""Device management API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.schemas import Command, DeviceInfo, DeviceStatus
from shared.schemas.messages import Heartbeat

router = APIRouter()


class CommandRequest(BaseModel):
    """Request body for sending commands."""

    action: str
    params: dict[str, Any] = {}
    priority: int = 0
    timeout_ms: int = 5000


class CommandSentResponse(BaseModel):
    """Response for command sent."""

    request_id: UUID
    device_id: str
    action: str
    status: str = "sent"


class DeviceListResponse(BaseModel):
    """Response for device list."""

    devices: list[DeviceInfo]
    total: int
    online: int


class DeviceDetailResponse(BaseModel):
    """Response for device details."""

    info: DeviceInfo
    status: DeviceStatus


@router.get("", response_model=DeviceListResponse)
async def list_devices() -> DeviceListResponse:
    """List all registered devices."""
    from server.api.main import get_device_registry

    registry = get_device_registry()
    devices = registry.get_all_devices()
    online = registry.get_online_devices()

    return DeviceListResponse(
        devices=devices,
        total=len(devices),
        online=len(online),
    )


@router.post("", response_model=DeviceInfo)
async def register_device(device: DeviceInfo) -> DeviceInfo:
    """Register a device via HTTP (for testing/simulation)."""
    from server.api.main import get_device_registry

    registry = get_device_registry()
    await registry.register_device(device)
    return device


@router.post("/{device_id}/heartbeat")
async def device_heartbeat(device_id: str, heartbeat: Heartbeat) -> dict[str, str]:
    """Send device heartbeat via HTTP (for testing/simulation)."""
    from server.api.main import get_device_registry

    registry = get_device_registry()
    await registry.update_heartbeat(
        device_id=heartbeat.device_id,
        uptime_ms=heartbeat.uptime_ms,
        load=heartbeat.load,
        memory_free=heartbeat.memory_free,
    )
    return {"status": "ok"}


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(device_id: str) -> DeviceDetailResponse:
    """Get device info and status."""
    from server.api.main import get_device_registry

    registry = get_device_registry()

    info = registry.get_device(device_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    status = registry.get_status(device_id)
    if not status:
        status = DeviceStatus(device_id=device_id)

    return DeviceDetailResponse(info=info, status=status)


@router.post("/{device_id}/command", response_model=CommandSentResponse)
async def send_command(device_id: str, request: CommandRequest) -> CommandSentResponse:
    """Send a command to a device."""
    from server.api.main import get_device_registry, get_zenoh_hub

    registry = get_device_registry()
    hub = get_zenoh_hub()

    # Verify device exists
    device = registry.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Create and send command
    command = Command(
        device_id=device_id,
        action=request.action,
        params=request.params,
        priority=request.priority,
        timeout_ms=request.timeout_ms,
    )

    await hub.send_command(device_id, command)

    return CommandSentResponse(
        request_id=command.request_id,
        device_id=device_id,
        action=request.action,
    )


@router.get("/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(device_id: str) -> DeviceStatus:
    """Get current device status."""
    from server.api.main import get_device_registry

    registry = get_device_registry()

    status = registry.get_status(device_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    return status


@router.delete("/{device_id}")
async def unregister_device(device_id: str) -> dict[str, str]:
    """Unregister a device."""
    from server.api.main import get_device_registry

    registry = get_device_registry()

    removed = await registry.unregister_device(device_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    return {"status": "unregistered", "device_id": device_id}
