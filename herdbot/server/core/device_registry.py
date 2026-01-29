"""Device registry for tracking connected devices.

Manages device registration, heartbeat tracking, and online/offline status.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import structlog

from shared.schemas import DeviceInfo, DeviceStatus
from shared.schemas.device import ConnectionStatus

logger = structlog.get_logger()


class DeviceRegistry:
    """Registry for managing connected devices.

    Tracks device registration, heartbeats, and status. Provides callbacks
    for device online/offline events.
    """

    def __init__(
        self,
        heartbeat_timeout_ms: int = 6000,
        cleanup_interval_s: int = 30,
    ) -> None:
        """Initialize the device registry.

        Args:
            heartbeat_timeout_ms: Time without heartbeat before device marked offline
            cleanup_interval_s: Interval for checking device health
        """
        self._devices: dict[str, DeviceInfo] = {}
        self._status: dict[str, DeviceStatus] = {}
        self._heartbeat_timeout = timedelta(milliseconds=heartbeat_timeout_ms)
        self._cleanup_interval = cleanup_interval_s
        self._cleanup_task: asyncio.Task[None] | None = None
        self._on_device_online: list[Callable[[str, DeviceInfo], Any]] = []
        self._on_device_offline: list[Callable[[str], Any]] = []
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the device registry background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("device_registry_started")

    async def stop(self) -> None:
        """Stop the device registry and cleanup."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("device_registry_stopped")

    def on_device_online(self, callback: Callable[[str, DeviceInfo], Any]) -> None:
        """Register callback for device online events."""
        self._on_device_online.append(callback)

    def on_device_offline(self, callback: Callable[[str], Any]) -> None:
        """Register callback for device offline events."""
        self._on_device_offline.append(callback)

    async def register_device(self, device_info: DeviceInfo) -> None:
        """Register a new device or update existing registration.

        Args:
            device_info: Device information to register
        """
        async with self._lock:
            device_id = device_info.device_id
            is_new = device_id not in self._devices
            was_offline = (
                device_id in self._status
                and self._status[device_id].status != ConnectionStatus.ONLINE
            )

            self._devices[device_id] = device_info

            if device_id not in self._status:
                self._status[device_id] = DeviceStatus(
                    device_id=device_id,
                    status=ConnectionStatus.ONLINE,
                    last_seen=datetime.utcnow(),
                )
            else:
                self._status[device_id].status = ConnectionStatus.ONLINE
                self._status[device_id].last_seen = datetime.utcnow()

            if is_new or was_offline:
                logger.info(
                    "device_online",
                    device_id=device_id,
                    device_type=device_info.device_type,
                    is_new=is_new,
                )
                for callback in self._on_device_online:
                    try:
                        result = callback(device_id, device_info)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error("device_online_callback_error", error=str(e))

    async def unregister_device(self, device_id: str) -> bool:
        """Unregister a device.

        Args:
            device_id: Device identifier to unregister

        Returns:
            True if device was found and removed
        """
        async with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                if device_id in self._status:
                    del self._status[device_id]
                logger.info("device_unregistered", device_id=device_id)
                return True
            return False

    async def update_heartbeat(
        self,
        device_id: str,
        uptime_ms: int = 0,
        load: float = 0.0,
        memory_free: int | None = None,
    ) -> None:
        """Update device heartbeat.

        Args:
            device_id: Device identifier
            uptime_ms: Device uptime in milliseconds
            load: CPU/resource load (0.0-1.0)
            memory_free: Free memory in bytes
        """
        async with self._lock:
            if device_id not in self._status:
                self._status[device_id] = DeviceStatus(device_id=device_id)

            status = self._status[device_id]
            was_offline = status.status != ConnectionStatus.ONLINE

            status.status = ConnectionStatus.ONLINE
            status.last_seen = datetime.utcnow()
            status.uptime_ms = uptime_ms

            if memory_free is not None:
                status.extra["memory_free"] = memory_free
            if load > 0:
                status.extra["load"] = load

            if was_offline and device_id in self._devices:
                logger.info("device_reconnected", device_id=device_id)
                for callback in self._on_device_online:
                    try:
                        result = callback(device_id, self._devices[device_id])
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error("device_online_callback_error", error=str(e))

    def get_device(self, device_id: str) -> DeviceInfo | None:
        """Get device info by ID."""
        return self._devices.get(device_id)

    def get_status(self, device_id: str) -> DeviceStatus | None:
        """Get device status by ID."""
        return self._status.get(device_id)

    def get_all_devices(self) -> list[DeviceInfo]:
        """Get all registered devices."""
        return list(self._devices.values())

    def get_all_statuses(self) -> list[DeviceStatus]:
        """Get status for all devices."""
        return list(self._status.values())

    def get_online_devices(self) -> list[DeviceInfo]:
        """Get all online devices."""
        return [
            self._devices[device_id]
            for device_id, status in self._status.items()
            if status.is_online() and device_id in self._devices
        ]

    async def _cleanup_loop(self) -> None:
        """Background task to check device health and mark offline."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._check_device_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("cleanup_loop_error", error=str(e))

    async def _check_device_health(self) -> None:
        """Check all devices and mark timed-out ones as offline."""
        now = datetime.utcnow()
        offline_devices: list[str] = []

        async with self._lock:
            for device_id, status in self._status.items():
                if status.status == ConnectionStatus.ONLINE and status.last_seen:
                    if now - status.last_seen > self._heartbeat_timeout:
                        status.status = ConnectionStatus.OFFLINE
                        offline_devices.append(device_id)

        # Trigger callbacks outside lock
        for device_id in offline_devices:
            logger.warning("device_offline", device_id=device_id)
            for callback in self._on_device_offline:
                try:
                    result = callback(device_id)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error("device_offline_callback_error", error=str(e))
