#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import contextlib
import os
import logging
import queue
import platform
import sys
import threading
import uuid
import time
from dateutil import tz
from datetime import datetime
from json import dumps
from typing import Any, Optional, Dict
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

try:
    import tomllib as tomli
except ImportError:
    tomli = None

logger = logging.getLogger(__name__)


def get_package_version() -> str:
    """Get version of package from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            if tomli:
                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)
                    return data["project"]["version"]
    except Exception as e:
        logger.error(f"Error getting package version: {e}")
    return "unknown"


PACKAGE_VERSION = get_package_version()


class EventType(str, Enum):
    """Type of telemetry events"""
    STARTUP = "startup"
    TOOL_EXECUTION = "tool_execution"
    PROMPT_GET = "prompt_get"
    RESOURCE_READ = "resource_read"
    ERROR = "error"
    SHUT_DOWN = "shutdown"


@dataclass
class TelemetryEvent:
    """Structure for telemetry event"""
    event_type: EventType
    customer_uuid: str
    session_id: str
    timestamp: float
    version: str
    platform: str

    tool_source: Optional[str] = None
    tool_name: Optional[str] = None
    prompt_name: Optional[str] = None
    prompt_text: Optional[str] = None
    resource_uri: Optional[str] = None
    success: bool = True
    elapsed_ms: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.date_data = datetime.fromtimestamp(
            self.timestamp, tz=tz.tzlocal()
        ).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class TelemetryCollectorConfig:
    collect_prompts: bool = True
    max_prompt_length: int = 200
    enabled: bool = False

    supabase_url: str = "https://yzasssndwqceclzilcdu.supabase.co"
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl6YXNzc25kd3FjZWNsemlsY2R1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA5MDc2NjQsImV4cCI6MjA3NjQ4MzY2NH0.SwFLQ-L0pgQC6bGC_PXCrCcDBYrF6QpZsvApj_Ogt7M"


class TelemetryCollector:
    """The telemetry collector class"""

    def __init__(self):
        self.config: TelemetryCollectorConfig = TelemetryCollectorConfig()

        if self._is_disabled():
            self.config.enabled = False
            logger.warning("Telemetry disabled via environment variable.")

        self._customer_uuid: str = self._get_customer_uuid()
        self._session_id: str = str(uuid.uuid4())

        self._queue: queue.Queue[TelemetryEvent] = queue.Queue(maxsize=1000)
        self._worker: threading.Thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name='Worker Thread',
            args=(),
            kwargs={}
        )
        self._worker.start()

        logger.warning(f"Telemetry initialized (enabled={self.config.enabled}, has_supabase={HAS_SUPABASE}, customer_uuid={self._customer_uuid})")

    def _is_disabled(self) -> bool:
        """Check if telemetry is disabled via environment variables"""
        disable_vars = [
            "DISABLE_TELEMETRY",
            "BLENDER_MCP_DISABLE_TELEMETRY",
            "MCP_DISABLE_TELEMETRY"
        ]

        for var in disable_vars:
            if os.environ.get(var, "").lower() in ("true", "1", "yes", "on"):
                return True
        return False

    def _get_customer_uuid(self) -> str:
        """Get or create anonymous customer UUID"""
        try:
            data_dir = self._get_data_directory()
            uuid_file = data_dir / 'customer_uuid.txt'

            if uuid_file.exists():
                customer_uuid = uuid_file.read_text(encoding="utf-8").strip()
                if customer_uuid:
                    return customer_uuid

            customer_uuid = str(uuid.uuid4())
            uuid_file.write_text(customer_uuid, encoding="utf-8")

            # Set restrictive permissions on Unix
            if sys.platform != "win32":
                os.chmod(uuid_file, 0o600)

            return customer_uuid
        except Exception as e:
            logger.debug(f"Error persisting customer UUID: {e}")
            return str(uuid.uuid4())

    def _get_data_directory(self) -> Path:
        """Get directory for storing telemetry data"""
        if sys.platform == "win32":
            base_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif sys.platform == "darwin":
            base_dir = Path.home() / '.local' / 'share'
        else:
            base_dir = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))

        data_dir = base_dir
        data_dir.mkdir(parents=True, exist_ok=True)

        return data_dir

    def record_event(
        self,
        event_type: EventType,
        tool_source: Optional[str] = None,
        tool_name: Optional[str] = None,
        prompt_name: Optional[str] = None,
        prompt_text: Optional[str] = None,
        resource_uri: Optional[str] = None,
        success: bool = True,
        elapsed_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a telemetry event"""
        logger.warning(f"Recording telemetry event: {event_type.value!r}")

        # Truncate prompt
        if prompt_text and len(prompt_text) > self.config.max_prompt_length:
            prompt_text = prompt_text[:self.config.max_prompt_length] + "..."

        # Truncate error messages
        if error_message and len(error_message) > 200:
            error_message = error_message[:200] + "..."

        event = TelemetryEvent(
            event_type=event_type,
            customer_uuid=self._customer_uuid,
            session_id=self._session_id,
            timestamp=time.time(),
            version=PACKAGE_VERSION,
            platform=platform.system().lower(),
            tool_source=tool_source,
            tool_name=tool_name,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            resource_uri=resource_uri,
            success=success,
            elapsed_ms=elapsed_ms,
            error_message=error_message,
            metadata=metadata
        )

        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.debug("Telemetry queue full, dropping event")

    def _worker_loop(self):
        """Background worker that sends telemetry."""
        while True:
            event = self._queue.get(block=True, timeout=None)
            try:
                self._send_event(event)
            except Exception as e:
                logger.debug(f"Error sending telemetry: {e}")
            finally:
                with contextlib.suppress(Exception):
                    self._queue.task_done()

    def _send_event(self, event: TelemetryEvent):
        try:
            data = {
                "customer_uuid": event.customer_uuid,
                "session_id": event.session_id,
                "event_type": event.event_type.value,
                "tool_source": event.tool_source,
                "tool_name": event.tool_name,
                "prompt_name": event.prompt_name,
                "prompt_text": event.prompt_text,
                "success": event.success,
                "elapsed_ms": event.elapsed_ms,
                "error_message": event.error_message,
                "version": event.version,
                "platform": event.platform,
                "metadata": event.metadata or {},
                "event_timestamp": int(event.timestamp),
                "datetime": event.date_data
            }

            if True or not HAS_SUPABASE:
                event_record_file = self._get_data_directory() / 'recorded_events.txt'
                with event_record_file.open(mode='a') as f:
                    f.write(dumps(data, indent=3))
                    f.write('\n\n')
                logger.info(f"Sent event {event.event_type.value!r} to file {str(event_record_file)!r}")
                return
                # Create Supabase client with explicit options

            from supabase import ClientOptions

            options = ClientOptions(
                auto_refresh_token=False,
                persist_session=False
            )

            supabase: Client = create_client(
                self.config.supabase_url,
                self.config.supabase_anon_key,
                options=options
            )

            _ = supabase.table("telemetry_events").insert(data, returning="minimal").execute()
            logger.debug(f"Telemetry sent: {event.event_type}")

        except Exception as e:
            logger.debug(f"Error sending telemetry event: {e}")


_telemetry_collector: Optional[TelemetryCollector] = None


def get_telemetry_collector() -> TelemetryCollector:
    global _telemetry_collector
    if _telemetry_collector is None:
        _telemetry_collector = TelemetryCollector()
    return _telemetry_collector


def record_tool_usage(
    tool_source: str,
    tool_name: str,
    success: bool,
    elapsed_ms: float,
    error: Optional[str] = None
):
    get_telemetry_collector().record_event(
        tool_source=tool_source,
        event_type=EventType.TOOL_EXECUTION,
        tool_name=tool_name,
        success=success,
        elapsed_ms=elapsed_ms,
        error_message=error
    )


def record_prompt_get(
    prompt_name: str,
    prompt_text: str,
    success: bool,
    elapsed_ms: float,
    error: Optional[str] = None
):
    get_telemetry_collector().record_event(
        event_type=EventType.PROMPT_GET,
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        success=success,
        elapsed_ms=elapsed_ms,
        error_message=error
    )


def record_resource_read(
    resource_uri: str,
    success: bool,
    elapsed_ms: float,
    error: Optional[str] = None
):
    get_telemetry_collector().record_event(
        event_type=EventType.RESOURCE_READ,
        resource_uri=resource_uri,
        success=success,
        elapsed_ms=elapsed_ms,
        error_message=error
    )


def record_startup():
    get_telemetry_collector().record_event(
        event_type=EventType.STARTUP
    )


def record_shutdown():
    get_telemetry_collector().record_event(
        event_type=EventType.SHUT_DOWN
    )
