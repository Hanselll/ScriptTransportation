"""SFTP and SSH based transfer helpers."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

from config import is_allowed_host
from utils import SecurityError, UploadError, ensure_parent_dir, setup_logger, timestamp_str

logger = setup_logger(__name__)


def _connect_ssh(server_ip: str, username: str, password: str) -> paramiko.SSHClient:
    if not is_allowed_host(server_ip):
        raise SecurityError(f"Server '{server_ip}' is not in ALLOWED_HOSTS.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(server_ip, username=username, password=password, timeout=15)
    except Exception as exc:
        raise UploadError(f"SSH connection failed to {server_ip}: {exc}") from exc
    return client


def _mkdir_remote(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = Path(remote_dir).parts
    current = "" if remote_dir.startswith("/") else "."
    for part in parts:
        if part == "/":
            current = "/"
            continue
        current = os.path.join(current, part) if current not in ("", "/") else f"/{part}" if current == "/" else part
        try:
            sftp.stat(current)
        except IOError:
            sftp.mkdir(current)


def upload_file(
    local_path: str,
    server_ip: str,
    username: str,
    password: str,
    remote_path: str,
) -> dict:
    logger.info("Start uploading file '%s' to '%s:%s'", local_path, server_ip, remote_path)
    local = Path(local_path)
    if not local.exists() or not local.is_file():
        raise UploadError(f"Local file not found: {local_path}")

    ssh_client = _connect_ssh(server_ip, username, password)
    sftp = None
    try:
        sftp = ssh_client.open_sftp()
        remote_target = Path(remote_path)
        if remote_path.endswith("/"):
            remote_file = str(remote_target / local.name)
        else:
            remote_file = remote_path if remote_target.suffix else str(remote_target / local.name)
        _mkdir_remote(sftp, str(Path(remote_file).parent))
        sftp.put(str(local), remote_file)
        logger.info("Upload finished: %s", remote_file)
        return {"status": "success", "remote_file": remote_file}
    except Exception as exc:
        raise UploadError(f"Upload failed: {exc}") from exc
    finally:
        if sftp:
            sftp.close()
        ssh_client.close()


def download_file(
    server_ip: str,
    username: str,
    password: str,
    remote_file: str,
    local_path: str,
) -> dict:
    logger.info("Start downloading file '%s:%s'", server_ip, remote_file)
    ensure_parent_dir(local_path)
    ssh_client = _connect_ssh(server_ip, username, password)
    sftp = None
    try:
        sftp = ssh_client.open_sftp()
        sftp.get(remote_file, local_path)
        logger.info("Download finished: %s", local_path)
        return {"status": "success", "local_file": local_path}
    except Exception as exc:
        raise UploadError(f"Download failed: {exc}") from exc
    finally:
        if sftp:
            sftp.close()
        ssh_client.close()


def download_directory_as_tar(
    server_ip: str,
    username: str,
    password: str,
    remote_dir: str,
    local_tar_path: str,
) -> dict:
    logger.info("Start downloading remote directory as tar: %s", remote_dir)
    ensure_parent_dir(local_tar_path)
    ssh_client = _connect_ssh(server_ip, username, password)
    sftp = None
    remote_tar = f"/tmp/remote_exec_plugin_{timestamp_str()}.tar.gz"
    try:
        tar_cmd = f"tar -czf {remote_tar} -C {Path(remote_dir).parent} {Path(remote_dir).name}"
        stdin, stdout, stderr = ssh_client.exec_command(tar_cmd)
        exit_code = stdout.channel.recv_exit_status()
        err = stderr.read().decode("utf-8", errors="replace")
        if exit_code != 0:
            raise UploadError(f"Remote tar command failed (exit={exit_code}): {err}")

        sftp = ssh_client.open_sftp()
        sftp.get(remote_tar, local_tar_path)
        ssh_client.exec_command(f"rm -f {remote_tar}")
        logger.info("Directory tar download finished: %s", local_tar_path)
        return {"status": "success", "local_tar": local_tar_path}
    except Exception as exc:
        raise UploadError(f"download_directory_as_tar failed: {exc}") from exc
    finally:
        if sftp:
            sftp.close()
        ssh_client.close()
