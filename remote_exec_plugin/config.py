"""Configuration and security helpers for remote_exec_plugin."""

from pathlib import Path


# Fixed shared root (no env override)
SHARED_ROOT = Path("/mnt/hgfs/agent_dropzone").resolve()
OUTBOX_DIR = SHARED_ROOT / "outbox"
REPORTS_DIR = SHARED_ROOT / "reports"
ARCHIVE_DIR = SHARED_ROOT / "archive"
FAILED_DIR = SHARED_ROOT / "failed"

MAX_FILE_SIZE = 100 * 1024 * 1024
FORBIDDEN_COMMAND_KEYWORDS = ["rm ", "shutdown", "reboot", "mkfs", ":(){:|:&};:"]


def get_allowed_hosts():
    """Compatibility helper: host restriction disabled by user request."""
    return ["*"]


def shared_path(*parts):
    """Build a path under SHARED_ROOT."""
    return SHARED_ROOT.joinpath(*parts)


def is_allowed_host(server_ip):
    """Host restriction disabled by user request."""
    return True


def is_command_safe(command):
    """Return True if command does not include forbidden keywords."""
    lower_command = command.lower()
    return not any(keyword.lower() in lower_command for keyword in FORBIDDEN_COMMAND_KEYWORDS)
