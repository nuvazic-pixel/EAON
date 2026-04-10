"""
EAON 2.0 — Centralized Configuration
=====================================
All settings from environment variables with sensible defaults.
Load .env file in main.py before importing this module.
"""

import os
from typing import Optional
from dataclasses import dataclass, field


def _bool(val: str) -> bool:
    """Parse boolean from env string."""
    return val.lower() in ("true", "1", "yes", "on")


def _list(val: str) -> list[str]:
    """Parse comma-separated list from env string."""
    return [x.strip() for x in val.split(",") if x.strip()]


@dataclass
class IntelConfig:
    """INTEL layer configuration."""
    enabled: bool = True
    
    # GeoIP
    geoip_db_path: str = "data/GeoLite2-City.mmdb"
    geoip_fallback_url: str = "http://ip-api.com/json/{ip}"
    
    # API Keys
    abuseipdb_api_key: Optional[str] = None
    otx_api_key: Optional[str] = None
    virustotal_api_key: Optional[str] = None
    
    # Risk country codes
    high_risk_cc: list[str] = field(default_factory=lambda: ["KP", "IR", "RU", "CN", "BY"])
    medium_risk_cc: list[str] = field(default_factory=lambda: ["VN", "PK", "NG", "UA", "RO"])
    
    # Cache settings
    cache_ttl_seconds: int = 3600
    cache_prefix: str = "intel:"
    
    @classmethod
    def from_env(cls) -> "IntelConfig":
        return cls(
            enabled=_bool(os.getenv("INTEL_ENABLED", "true")),
            geoip_db_path=os.getenv("GEOIP_DB_PATH", "data/GeoLite2-City.mmdb"),
            geoip_fallback_url=os.getenv("GEOIP_FALLBACK_URL", "http://ip-api.com/json/{ip}"),
            abuseipdb_api_key=os.getenv("ABUSEIPDB_API_KEY"),
            otx_api_key=os.getenv("OTX_API_KEY"),
            virustotal_api_key=os.getenv("VIRUSTOTAL_API_KEY"),
            high_risk_cc=_list(os.getenv("INTEL_HIGH_RISK_CC", "KP,IR,RU,CN,BY")),
            medium_risk_cc=_list(os.getenv("INTEL_MEDIUM_RISK_CC", "VN,PK,NG,UA,RO")),
            cache_ttl_seconds=int(os.getenv("INTEL_CACHE_TTL", "3600")),
            cache_prefix=os.getenv("INTEL_CACHE_PREFIX", "intel:"),
        )


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    enabled: bool = True
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            enabled=_bool(os.getenv("REDIS_ENABLED", "true")),
        )
    
    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class SlackConfig:
    """Slack integration configuration."""
    enabled: bool = False
    webhook_url: Optional[str] = None
    channel: str = "#eaon-alerts"
    username: str = "EAON"
    icon_emoji: str = ":robot_face:"
    
    # Notification thresholds
    notify_on_block: bool = True
    notify_on_review: bool = True
    notify_on_high_risk: bool = True
    high_risk_threshold: int = 40
    
    @classmethod
    def from_env(cls) -> "SlackConfig":
        return cls(
            enabled=_bool(os.getenv("SLACK_ENABLED", "false")),
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            channel=os.getenv("SLACK_CHANNEL", "#eaon-alerts"),
            username=os.getenv("SLACK_USERNAME", "EAON"),
            icon_emoji=os.getenv("SLACK_ICON_EMOJI", ":robot_face:"),
            notify_on_block=_bool(os.getenv("SLACK_NOTIFY_BLOCK", "true")),
            notify_on_review=_bool(os.getenv("SLACK_NOTIFY_REVIEW", "true")),
            notify_on_high_risk=_bool(os.getenv("SLACK_NOTIFY_HIGH_RISK", "true")),
            high_risk_threshold=int(os.getenv("SLACK_HIGH_RISK_THRESHOLD", "40")),
        )


@dataclass
class JiraConfig:
    """JIRA integration configuration."""
    enabled: bool = False
    server_url: Optional[str] = None
    username: Optional[str] = None
    api_token: Optional[str] = None
    project_key: str = "SEC"
    issue_type: str = "Task"
    
    # Auto-create tickets
    create_on_block: bool = True
    create_on_high_risk: bool = True
    high_risk_threshold: int = 50
    
    @classmethod
    def from_env(cls) -> "JiraConfig":
        return cls(
            enabled=_bool(os.getenv("JIRA_ENABLED", "false")),
            server_url=os.getenv("JIRA_SERVER_URL"),
            username=os.getenv("JIRA_USERNAME"),
            api_token=os.getenv("JIRA_API_TOKEN"),
            project_key=os.getenv("JIRA_PROJECT_KEY", "SEC"),
            issue_type=os.getenv("JIRA_ISSUE_TYPE", "Task"),
            create_on_block=_bool(os.getenv("JIRA_CREATE_ON_BLOCK", "true")),
            create_on_high_risk=_bool(os.getenv("JIRA_CREATE_ON_HIGH_RISK", "true")),
            high_risk_threshold=int(os.getenv("JIRA_HIGH_RISK_THRESHOLD", "50")),
        )


@dataclass
class OrchestratorConfig:
    """Core orchestrator configuration."""
    default_model: str = "llama3"
    fallback_model: str = "mistral"
    safe_mode_model: str = "mistral"
    
    # Risk-based mode switching
    high_risk_threshold: int = 40
    medium_risk_threshold: int = 20
    
    # Execution
    timeout_seconds: int = 30
    max_retries: int = 2
    enable_critic: bool = True
    
    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        return cls(
            default_model=os.getenv("EAON_DEFAULT_MODEL", "llama3"),
            fallback_model=os.getenv("EAON_FALLBACK_MODEL", "mistral"),
            safe_mode_model=os.getenv("EAON_SAFE_MODE_MODEL", "mistral"),
            high_risk_threshold=int(os.getenv("EAON_HIGH_RISK_THRESHOLD", "40")),
            medium_risk_threshold=int(os.getenv("EAON_MEDIUM_RISK_THRESHOLD", "20")),
            timeout_seconds=int(os.getenv("EAON_TIMEOUT", "30")),
            max_retries=int(os.getenv("EAON_MAX_RETRIES", "2")),
            enable_critic=_bool(os.getenv("EAON_ENABLE_CRITIC", "true")),
        )


@dataclass
class LogConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"  # json or console
    file_path: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO").upper(),
            format=os.getenv("LOG_FORMAT", "json"),
            file_path=os.getenv("LOG_FILE"),
        )


@dataclass
class Settings:
    """Master settings container."""
    intel: IntelConfig
    redis: RedisConfig
    slack: SlackConfig
    jira: JiraConfig
    orchestrator: OrchestratorConfig
    log: LogConfig
    
    # App metadata
    app_name: str = "EAON"
    version: str = "2.0.0"
    environment: str = "development"
    debug: bool = False
    
    @classmethod
    def load(cls) -> "Settings":
        """Load all settings from environment."""
        return cls(
            intel=IntelConfig.from_env(),
            redis=RedisConfig.from_env(),
            slack=SlackConfig.from_env(),
            jira=JiraConfig.from_env(),
            orchestrator=OrchestratorConfig.from_env(),
            log=LogConfig.from_env(),
            app_name=os.getenv("APP_NAME", "EAON"),
            version=os.getenv("APP_VERSION", "2.0.0"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=_bool(os.getenv("DEBUG", "false")),
        )


# Singleton instance — import this
settings: Settings = None


def init_settings() -> Settings:
    """Initialize settings (call after loading .env)."""
    global settings
    settings = Settings.load()
    return settings


def get_settings() -> Settings:
    """Get settings instance, initializing if needed."""
    global settings
    if settings is None:
        settings = Settings.load()
    return settings
