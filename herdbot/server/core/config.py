"""Configuration management for herdbot server.

Uses Pydantic Settings for configuration with environment variable support.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be overridden via environment variables with HERDBOT_ prefix.
    Example: HERDBOT_API_PORT=8080
    """

    model_config = SettingsConfigDict(
        env_prefix="HERDBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Server identification
    server_id: str = Field(default="herdbot-server-01", description="Unique server identifier")
    instance_number: int = Field(default=1, description="Instance number for HA deployments")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API bind address")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # Zenoh settings
    zenoh_mode: str = Field(default="peer", description="Zenoh mode: peer, client, router")
    zenoh_listen: list[str] = Field(
        default=["tcp/0.0.0.0:7447"], description="Zenoh listen endpoints"
    )
    zenoh_connect: list[str] = Field(default=[], description="Zenoh connect endpoints")

    # MQTT bridge settings (for ESP32/Pico clients)
    mqtt_enabled: bool = Field(default=True, description="Enable MQTT bridge")
    mqtt_host: str = Field(default="0.0.0.0", description="MQTT broker bind address")
    mqtt_port: int = Field(default=1883, description="MQTT broker port")

    # Device management
    heartbeat_interval_ms: int = Field(default=2000, description="Expected heartbeat interval")
    heartbeat_timeout_ms: int = Field(default=6000, description="Heartbeat timeout for offline")
    device_cleanup_interval_s: int = Field(default=30, description="Device cleanup check interval")

    # Topic prefixes
    topic_prefix: str = Field(default="herd", description="Base topic prefix")

    # AI settings
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")
    default_ai_provider: str = Field(default="openai", description="Default AI provider")

    # Visualization
    rerun_enabled: bool = Field(default=True, description="Enable Rerun integration")
    rerun_recording_id: str = Field(default="herdbot", description="Rerun recording ID")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or console")

    # Paths
    data_dir: Path = Field(default=Path("./data"), description="Data directory")

    @property
    def topic_devices(self) -> str:
        """Topic pattern for device messages."""
        return f"{self.topic_prefix}/devices"

    @property
    def topic_sensors(self) -> str:
        """Topic pattern for sensor messages."""
        return f"{self.topic_prefix}/sensors"

    @property
    def topic_commands(self) -> str:
        """Topic pattern for command messages."""
        return f"{self.topic_prefix}/commands"

    @property
    def topic_ai(self) -> str:
        """Topic pattern for AI messages."""
        return f"{self.topic_prefix}/ai"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
