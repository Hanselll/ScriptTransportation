"""Tool-facing wrappers for agent integration."""

from __future__ import annotations

from report_fetcher import fetch_report
from report_parser import analyze_report
from shared_storage import read_shared_file, resolve_shared_path
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
) -> dict:
    local_path = resolve_shared_path(file_key)
    return upload_file(local_path, server_ip, username, password, remote_path)


def tool_run_remote_command(
    server_ip: str,
    username: str,
    password: str,
    command: str,
) -> dict:
    return run_remote_command(server_ip, username, password, command)


def tool_fetch_report(
    server_ip: str,
    username: str,
    password: str,
    remote_report_path: str,
    local_report_key: str,
) -> dict:
    return fetch_report(server_ip, username, password, remote_report_path, local_report_key)


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
    )
