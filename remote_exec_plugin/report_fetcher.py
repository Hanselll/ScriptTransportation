"""Report fetch and extraction logic."""

from __future__ import annotations

from pathlib import Path

import paramiko

from config import SHARED_ROOT, is_allowed_host
from sftp_transfer import download_directory_as_tar, download_file
from utils import ReportFetchError, SecurityError, extract_tar_gz, list_files_recursive, safe_mkdir, setup_logger

logger = setup_logger(__name__)


def _is_remote_directory(server_ip: str, username: str, password: str, remote_path: str) -> bool:
    if not is_allowed_host(server_ip):
        raise SecurityError(f"Server '{server_ip}' is not in ALLOWED_HOSTS.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(server_ip, username=username, password=password, timeout=15)
        _, stdout, _ = client.exec_command(f"if [ -d '{remote_path}' ]; then echo DIR; else echo FILE; fi")
        result = stdout.read().decode("utf-8", errors="replace").strip()
        return result == "DIR"
    except Exception as exc:
        raise ReportFetchError(f"Failed to inspect remote report path: {exc}") from exc
    finally:
        client.close()


def fetch_report(
    server_ip: str,
    username: str,
    password: str,
    remote_report_path: str,
    local_report_key: str,
) -> dict:
    logger.info("Start fetching report from %s:%s", server_ip, remote_report_path)
    if local_report_key.startswith("/"):
        raise ReportFetchError("local_report_key must be relative, such as 'reports/job_001'.")

    local_report_dir = (SHARED_ROOT / local_report_key).resolve()
    try:
        local_report_dir.relative_to(SHARED_ROOT.resolve())
    except ValueError as exc:
        raise SecurityError("local_report_key resolves outside SHARED_ROOT.") from exc

    safe_mkdir(local_report_dir)

    try:
        if _is_remote_directory(server_ip, username, password, remote_report_path):
            local_tar = str(local_report_dir / "report_bundle.tar.gz")
            download_directory_as_tar(
                server_ip=server_ip,
                username=username,
                password=password,
                remote_dir=remote_report_path,
                local_tar_path=local_tar,
            )
            extract_tar_gz(local_tar, local_report_dir)
        else:
            file_name = Path(remote_report_path).name or "report.txt"
            local_file = str(local_report_dir / file_name)
            download_file(
                server_ip=server_ip,
                username=username,
                password=password,
                remote_file=remote_report_path,
                local_path=local_file,
            )

        artifacts = list_files_recursive(local_report_dir)
        logger.info("Fetch report completed with %d artifact(s).", len(artifacts))
        return {
            "status": "success",
            "local_report_dir": str(local_report_dir),
            "artifacts": artifacts,
        }
    except Exception as exc:
        raise ReportFetchError(f"fetch_report failed: {exc}") from exc
