"""FastAPI application setup for herdbot.

Provides REST API and WebSocket endpoints for external integrations.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.core import DeviceRegistry, Settings, ZenohHub, get_settings

from .routes import ai, devices, telemetry

logger = structlog.get_logger()

# Global instances (initialized in lifespan)
zenoh_hub: ZenohHub | None = None
device_registry: DeviceRegistry | None = None


def get_zenoh_hub() -> ZenohHub:
    """Get the Zenoh hub instance."""
    if zenoh_hub is None:
        raise RuntimeError("Zenoh hub not initialized")
    return zenoh_hub


def get_device_registry() -> DeviceRegistry:
    """Get the device registry instance."""
    if device_registry is None:
        raise RuntimeError("Device registry not initialized")
    return device_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global zenoh_hub, device_registry

    settings = get_settings()

    # Initialize components
    device_registry = DeviceRegistry(
        heartbeat_timeout_ms=settings.heartbeat_timeout_ms,
        cleanup_interval_s=settings.device_cleanup_interval_s,
    )
    zenoh_hub = ZenohHub(settings, device_registry)

    # Start services
    await device_registry.start()
    await zenoh_hub.start()

    logger.info(
        "application_started",
        server_id=settings.server_id,
        api_port=settings.api_port,
    )

    yield

    # Shutdown
    await zenoh_hub.stop()
    await device_registry.stop()

    logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override

    Returns:
        Configured FastAPI application
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Herdbot API",
        description="Lightweight robotics framework REST API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(devices.router, prefix="/devices", tags=["devices"])
    app.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
    app.include_router(ai.router, prefix="/ai", tags=["ai"])

    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint."""
        hub = get_zenoh_hub()
        registry = get_device_registry()

        return {
            "status": "healthy",
            "zenoh": {
                "running": hub.is_running,
                "session_id": hub.session_id,
            },
            "devices": {
                "total": len(registry.get_all_devices()),
                "online": len(registry.get_online_devices()),
            },
        }

    @app.get("/")
    async def root() -> RedirectResponse:
        """Redirect to dashboard."""
        return RedirectResponse(url="/dashboard")

    # Mount dashboard static files if they exist
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "static"
    if dashboard_path.exists():
        app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

    return app


# For running with uvicorn directly
app = create_app()
