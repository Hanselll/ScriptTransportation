"""Report fetch and extraction logic."""


from pathlib import Path

from config import SHARED_ROOT, is_allowed_host
from sftp_transfer import download_directory_as_tar, download_file
from utils import ReportFetchError, SecurityError, extract_tar_gz, list_files_recursive, safe_mkdir, setup_logger, require_command, run_cmd

logger = setup_logger(__name__)


def _is_remote_directory(server_ip, username, password, remote_path):
    if not is_allowed_host(server_ip):
        raise SecurityError("Server '{0}' is not in ALLOWED_HOSTS.".format(server_ip))
    require_command("ssh")
    require_command("sshpass")
    check_cmd = "if [ -d '{0}' ]; then echo DIR; else echo FILE; fi".format(str(remote_path).replace("'", "'\\''"))
    cmd = [
        "sshpass", "-p", password,
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "{0}@{1}".format(username, server_ip),
        check_cmd,
    ]
    code, out, err = run_cmd(cmd, timeout=60)
    if code != 0:
        raise ReportFetchError("Failed to inspect remote report path: {0}".format(err.strip()))
    return out.strip() == "DIR"


def fetch_report(server_ip, username, password, remote_report_path, local_report_key):
    logger.info("Start fetching report from %s:%s", server_ip, remote_report_path)
    if local_report_key.startswith("/"):
        raise ReportFetchError("local_report_key must be relative, such as 'reports/job_001'.")

    local_report_dir = (SHARED_ROOT / local_report_key).resolve()
    try:
        local_report_dir.relative_to(SHARED_ROOT.resolve())
    except ValueError:
        raise SecurityError("local_report_key resolves outside SHARED_ROOT.")

    safe_mkdir(local_report_dir)

    try:
        if _is_remote_directory(server_ip, username, password, remote_report_path):
            local_tar = str(local_report_dir / "report_bundle.tar.gz")
            download_directory_as_tar(server_ip, username, password, remote_report_path, local_tar)
            extract_tar_gz(local_tar, local_report_dir)
        else:
            file_name = Path(remote_report_path).name or "report.txt"
            local_file = str(local_report_dir / file_name)
            download_file(server_ip, username, password, remote_report_path, local_file)

        artifacts = list_files_recursive(local_report_dir)
        return {"status": "success", "local_report_dir": str(local_report_dir), "artifacts": artifacts}
    except Exception as exc:
        raise ReportFetchError("fetch_report failed: {0}".format(exc))
