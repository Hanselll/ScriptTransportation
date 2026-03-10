"""Configuration and security helpers for remote_exec_plugin."""

import os
from pathlib import Path


DEFAULT_SHARED_ROOT = "/mnt/hgfs/agent_dropzone"
DEFAULT_ALLOWED_HOSTS = ["10.217.8.238", "10.217.8.239"]


SHARED_ROOT = Path(os.environ.get("REMOTE_EXEC_SHARED_ROOT", DEFAULT_SHARED_ROOT)).resolve()
OUTBOX_DIR = SHARED_ROOT / "outbox"
REPORTS_DIR = SHARED_ROOT / "reports"
ARCHIVE_DIR = SHARED_ROOT / "archive"
FAILED_DIR = SHARED_ROOT / "failed"

MAX_FILE_SIZE = 100 * 1024 * 1024
FORBIDDEN_COMMAND_KEYWORDS = ["rm ", "shutdown", "reboot", "mkfs", ":(){:|:&};:"]


def get_allowed_hosts():
    """Return effective whitelist from env or defaults.

    - REMOTE_EXEC_ALLOWED_HOSTS supports comma-separated hosts.
    - If set to "*", all hosts are allowed.
    """
    raw = os.environ.get("REMOTE_EXEC_ALLOWED_HOSTS", "")
    if not raw.strip():
        return list(DEFAULT_ALLOWED_HOSTS)

    if raw.strip() == "*":
        return ["*"]

    hosts = [item.strip() for item in raw.split(",") if item.strip()]
    return hosts or list(DEFAULT_ALLOWED_HOSTS)


def shared_path(*parts):
    """Build a path under SHARED_ROOT."""
    return SHARED_ROOT.joinpath(*parts)


def is_allowed_host(server_ip):
    """Return True when server_ip is in effective whitelist."""
    allowed_hosts = get_allowed_hosts()
    return "*" in allowed_hosts or server_ip in allowed_hosts


def is_command_safe(command):
    """Return True if command does not include forbidden keywords."""
    lower_command = command.lower()
    return not any(keyword.lower() in lower_command for keyword in FORBIDDEN_COMMAND_KEYWORDS)
