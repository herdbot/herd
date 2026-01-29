#!/usr/bin/env python3
"""Herdbot CLI - Command-line interface for herdbot operations.

Usage:
    herdbot start              Start the server
    herdbot devices            List connected devices
    herdbot send <device> <cmd> Send a command to a device
    herdbot monitor <device>   Stream telemetry to terminal
    herdbot logs               View system logs
"""

import asyncio
import json
import sys
from typing import Any

import click
import httpx

# Default server URL
DEFAULT_URL = "http://localhost:8000"


def get_client(url: str) -> httpx.Client:
    """Create HTTP client."""
    return httpx.Client(base_url=url, timeout=30.0)


def get_async_client(url: str) -> httpx.AsyncClient:
    """Create async HTTP client."""
    return httpx.AsyncClient(base_url=url, timeout=30.0)


@click.group()
@click.option("--url", "-u", default=DEFAULT_URL, help="Server URL")
@click.pass_context
def cli(ctx: click.Context, url: str) -> None:
    """Herdbot CLI - Lightweight robotics framework."""
    ctx.ensure_object(dict)
    ctx.obj["url"] = url


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", help="Bind address")
@click.option("--port", "-p", default=8000, help="Port number")
@click.option("--workers", "-w", default=1, help="Number of workers")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def start(host: str, port: int, workers: int, reload: bool) -> None:
    """Start the herdbot server."""
    import uvicorn

    click.echo(f"Starting herdbot server on {host}:{port}")

    uvicorn.run(
        "server.api.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level="info",
    )


@cli.command()
@click.pass_context
def devices(ctx: click.Context) -> None:
    """List all registered devices."""
    url = ctx.obj["url"]

    try:
        with get_client(url) as client:
            response = client.get("/devices")
            response.raise_for_status()
            data = response.json()

            if not data["devices"]:
                click.echo("No devices registered")
                return

            click.echo(f"\nDevices ({data['online']}/{data['total']} online):\n")
            click.echo(f"{'ID':<20} {'Type':<15} {'Status':<10} {'Name'}")
            click.echo("-" * 60)

            for device in data["devices"]:
                device_id = device.get("device_id", "unknown")
                device_type = device.get("device_type", "unknown")
                name = device.get("name", "-")

                # Get status
                status_resp = client.get(f"/devices/{device_id}/status")
                status = "unknown"
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status", "unknown")

                status_color = "green" if status == "online" else "red"
                click.echo(
                    f"{device_id:<20} {device_type:<15} "
                    f"{click.style(status, fg=status_color):<10} {name}"
                )

    except httpx.ConnectError:
        click.echo(f"Error: Cannot connect to server at {url}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("device_id")
@click.argument("action")
@click.option("--params", "-p", default="{}", help="Command parameters as JSON")
@click.pass_context
def send(ctx: click.Context, device_id: str, action: str, params: str) -> None:
    """Send a command to a device."""
    url = ctx.obj["url"]

    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON parameters", err=True)
        sys.exit(1)

    try:
        with get_client(url) as client:
            response = client.post(
                f"/devices/{device_id}/command",
                json={"action": action, "params": params_dict},
            )

            if response.status_code == 404:
                click.echo(f"Error: Device '{device_id}' not found", err=True)
                sys.exit(1)

            response.raise_for_status()
            data = response.json()

            click.echo(f"Command sent: {action}")
            click.echo(f"Request ID: {data['request_id']}")

    except httpx.ConnectError:
        click.echo(f"Error: Cannot connect to server at {url}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("device_id")
@click.option("--format", "-f", type=click.Choice(["json", "simple"]), default="simple")
@click.pass_context
def monitor(ctx: click.Context, device_id: str, format: str) -> None:
    """Stream telemetry from a device to the terminal."""
    url = ctx.obj["url"]

    async def stream():
        import websockets

        ws_url = url.replace("http://", "ws://").replace("https://", "wss://")

        click.echo(f"Connecting to {device_id}...")

        try:
            async with websockets.connect(
                f"{ws_url}/telemetry/stream/{device_id}"
            ) as ws:
                click.echo("Connected. Streaming telemetry (Ctrl+C to stop):\n")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    if data.get("type") == "keepalive":
                        continue

                    if format == "json":
                        click.echo(json.dumps(data, indent=2))
                    else:
                        sensor = data.get("sensor_type", "unknown")
                        value = data.get("value", "?")
                        unit = data.get("unit", "")
                        ts = data.get("timestamp", "")[:19]

                        if isinstance(value, dict):
                            value = json.dumps(value)
                        elif isinstance(value, list):
                            value = ", ".join(str(v) for v in value[:3])

                        click.echo(f"[{ts}] {sensor}: {value} {unit}")

        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    try:
        asyncio.run(stream())
    except KeyboardInterrupt:
        click.echo("\nStopped")


@cli.command()
@click.option("--level", "-l", default="INFO", help="Log level filter")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.pass_context
def logs(ctx: click.Context, level: str, follow: bool) -> None:
    """View system logs."""
    click.echo("Log viewing requires direct server access or log aggregation.")
    click.echo("For development, use: HERDBOT_LOG_LEVEL=DEBUG herdbot start")


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Check server health."""
    url = ctx.obj["url"]

    try:
        with get_client(url) as client:
            response = client.get("/health")
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "unknown")
            color = "green" if status == "healthy" else "red"

            click.echo(f"Status: {click.style(status, fg=color)}")
            click.echo(f"Zenoh: {'running' if data['zenoh']['running'] else 'stopped'}")
            click.echo(f"Session: {data['zenoh']['session_id'] or 'N/A'}")
            click.echo(f"Devices: {data['devices']['online']}/{data['devices']['total']} online")

    except httpx.ConnectError:
        click.echo(f"Error: Cannot connect to server at {url}", err=True)
        click.echo("Status: " + click.style("offline", fg="red"))
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("message")
@click.option("--provider", "-p", help="AI provider to use")
@click.pass_context
def ask(ctx: click.Context, message: str, provider: str | None) -> None:
    """Ask the AI assistant a question."""
    url = ctx.obj["url"]

    try:
        with get_client(url) as client:
            payload: dict[str, Any] = {"message": message}
            if provider:
                payload["provider"] = provider

            response = client.post("/ai/chat", json=payload)

            if response.status_code == 503:
                click.echo("AI service unavailable. Configure API keys.", err=True)
                sys.exit(1)

            response.raise_for_status()
            data = response.json()

            click.echo(f"\n{data['response']}\n")
            click.echo(click.style(f"[{data['provider']}/{data['model']}]", dim=True))

    except httpx.ConnectError:
        click.echo(f"Error: Cannot connect to server at {url}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
