"""SSH command execution module."""

from __future__ import annotations

import socket

import paramiko

from config import is_allowed_host, is_command_safe
from utils import RemoteExecError, SecurityError, setup_logger

logger = setup_logger(__name__)


def run_remote_command(
    server_ip: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 600,
) -> dict:
    if not is_allowed_host(server_ip):
        raise SecurityError(f"Server '{server_ip}' is not in ALLOWED_HOSTS.")
    if not is_command_safe(command):
        raise SecurityError("Command rejected by safety policy.")

    logger.info("Running remote command on %s: %s", server_ip, command)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(server_ip, username=username, password=password, timeout=15)
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        return {
            "exit_code": exit_code,
            "stdout": out,
            "stderr": err,
            "command": command,
        }
    except socket.timeout as exc:
        raise RemoteExecError(f"Remote command timeout after {timeout}s.") from exc
    except paramiko.SSHException as exc:
        raise RemoteExecError(f"SSH execution failed: {exc}") from exc
    except Exception as exc:
        raise RemoteExecError(f"Remote execution error: {exc}") from exc
    finally:
        client.close()
