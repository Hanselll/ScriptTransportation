"""Tool-facing wrappers for agent integration."""

import base64
import binascii
import os
import tempfile

from report_fetcher import fetch_report
from report_parser import analyze_report
from shared_storage import read_shared_file
from sftp_transfer import upload_file
from ssh_executor import run_remote_command
from workflow import run_full_job


def tool_read_shared_file(file_key: str) -> dict:
    return read_shared_file(file_key)


def tool_upload_file(
    file_key: str,
    server_ip: str,
    username: str,
    password: str,
    remote_path: str,
    ssh_port: int = 22,
) -> dict:
    local_path = file_key
    return upload_file(local_path, server_ip, username, password, remote_path, ssh_port=ssh_port)


def tool_upload_file_content(
    file_name: str,
    content_base64: str,
    server_ip: str,
    username: str,
    password: str,
    remote_path: str,
    ssh_port: int = 22,
) -> dict:
    """Upload file content directly (no dependency on API server local filesystem)."""
    if not file_name:
        raise ValueError("file_name is required")
    if not content_base64:
        raise ValueError("content_base64 is required")

    base_name = os.path.basename(file_name)
    suffix = os.path.splitext(base_name)[1]
    fd, temp_path = tempfile.mkstemp(prefix="remote_exec_upload_", suffix=suffix)
    os.close(fd)
    try:
        try:
            raw = base64.b64decode(content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("content_base64 is invalid base64 text (example error: Incorrect padding).")
        with open(temp_path, "wb") as fh:
            fh.write(raw)

        if remote_path.endswith("/"):
            target_remote = remote_path + base_name
        else:
            target_remote = remote_path

        return upload_file(temp_path, server_ip, username, password, target_remote, ssh_port=ssh_port)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def tool_run_remote_command(
    server_ip: str,
    username: str,
    password: str,
    command: str,
    ssh_port: int = 22,
) -> dict:
    return run_remote_command(server_ip, username, password, command, ssh_port=ssh_port)


def tool_fetch_report(
    server_ip: str,
    username: str,
    password: str,
    remote_report_path: str,
    local_report_key: str,
    ssh_port: int = 22,
) -> dict:
    return fetch_report(server_ip, username, password, remote_report_path, local_report_key, ssh_port=ssh_port)


def tool_analyze_report(report_path: str) -> dict:
    return analyze_report(report_path)


def tool_run_full_job(
    file_key: str,
    server_ip: str,
    username: str,
    password: str,
    remote_path: str,
    run_command: str,
    remote_report_path: str,
    local_report_key: str,
    ssh_port: int = 22,
) -> dict:
    return run_full_job(
        file_key=file_key,
        server_ip=server_ip,
        username=username,
        password=password,
        remote_path=remote_path,
        run_command=run_command,
        remote_report_path=remote_report_path,
        local_report_key=local_report_key,
        ssh_port=ssh_port,
    )
