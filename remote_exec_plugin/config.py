"""Configuration and security helpers for remote_exec_plugin."""


from pathlib import Path

SHARED_ROOT = Path("/mnt/hgfs/agent_dropzone")
OUTBOX_DIR = SHARED_ROOT / "outbox"
REPORTS_DIR = SHARED_ROOT / "reports"
ARCHIVE_DIR = SHARED_ROOT / "archive"
FAILED_DIR = SHARED_ROOT / "failed"

ALLOWED_HOSTS = ["10.217.8.238", "10.217.8.239"]
MAX_FILE_SIZE = 100 * 1024 * 1024
FORBIDDEN_COMMAND_KEYWORDS = ["rm ", "shutdown", "reboot", "mkfs", ":(){:|:&};:"]


def shared_path(*parts: str) -> Path:
    """Build a path under SHARED_ROOT."""
    return SHARED_ROOT.joinpath(*parts)


def is_allowed_host(server_ip: str) -> bool:
    """Return True when server_ip is in explicit whitelist."""
    return server_ip in ALLOWED_HOSTS


def is_command_safe(command: str) -> bool:
    """Return True if command does not include forbidden keywords."""
    lower_command = command.lower()
    return not any(keyword.lower() in lower_command for keyword in FORBIDDEN_COMMAND_KEYWORDS)
