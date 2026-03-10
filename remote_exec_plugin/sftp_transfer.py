"""SSH/SFTP transfer helpers implemented with system ssh/scp commands."""

import os
from pathlib import Path

from config import is_allowed_host
from utils import SecurityError, UploadError, ensure_parent_dir, require_command, run_cmd, setup_logger, shell_quote, timestamp_str

logger = setup_logger(__name__)


def _base_sshpass(password):
    require_command("ssh")
    require_command("scp")
    require_command("sshpass")
    return ["sshpass", "-p", password]


def _validate_host(server_ip):
    if not is_allowed_host(server_ip):
        raise SecurityError("Server '{0}' is not in ALLOWED_HOSTS.".format(server_ip))


def _ssh_exec(server_ip, username, password, command, timeout=120):
    cmd = _base_sshpass(password) + [
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "{0}@{1}".format(username, server_ip),
        command,
    ]
    return run_cmd(cmd, timeout=timeout)


def upload_file(local_path, server_ip, username, password, remote_path):
    _validate_host(server_ip)
    local = Path(local_path)
    if not local.is_file():
        parent = str(local.parent)
        parent_exists = os.path.isdir(parent)
        hint = (
            "This path is checked on the API server machine. "
            "If the file is on the curl client machine, use /tool/upload_file_content instead."
        )
        raise UploadError(
            "Local file not found: {0}; parent_exists={1}; cwd={2}. {3}".format(
                local_path, parent_exists, os.getcwd(), hint
            )
        )

    remote_target = Path(remote_path)
    if remote_path.endswith("/") or not remote_target.suffix:
        remote_file = str(remote_target / local.name)
    else:
        remote_file = remote_path

    remote_dir = str(Path(remote_file).parent)
    mkdir_cmd = "mkdir -p {0}".format(shell_quote(remote_dir))
    code, _, err = _ssh_exec(server_ip, username, password, mkdir_cmd)
    if code != 0:
        raise UploadError("Failed to create remote directory: {0}".format(err.strip()))

    cmd = _base_sshpass(password) + [
        "scp",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        str(local),
        "{0}@{1}:{2}".format(username, server_ip, remote_file),
    ]
    code, _, err = run_cmd(cmd, timeout=300)
    if code != 0:
        raise UploadError("Upload failed: {0}".format(err.strip()))

    logger.info("Upload finished: %s", remote_file)
    return {"status": "success", "remote_file": remote_file}


def download_file(server_ip, username, password, remote_file, local_path):
    _validate_host(server_ip)
    ensure_parent_dir(local_path)

    cmd = _base_sshpass(password) + [
        "scp",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "{0}@{1}:{2}".format(username, server_ip, remote_file),
        local_path,
    ]
    code, _, err = run_cmd(cmd, timeout=300)
    if code != 0:
        raise UploadError("Download failed: {0}".format(err.strip()))

    logger.info("Download finished: %s", local_path)
    return {"status": "success", "local_file": local_path}


def download_directory_as_tar(server_ip, username, password, remote_dir, local_tar_path):
    _validate_host(server_ip)
    ensure_parent_dir(local_tar_path)

    remote_tar = "/tmp/remote_exec_plugin_{0}.tar.gz".format(timestamp_str())
    tar_cmd = "tar -czf {tar} -C {parent} {name}".format(
        tar=shell_quote(remote_tar),
        parent=shell_quote(str(Path(remote_dir).parent)),
        name=shell_quote(str(Path(remote_dir).name)),
    )
    code, _, err = _ssh_exec(server_ip, username, password, tar_cmd, timeout=600)
    if code != 0:
        raise UploadError("Remote tar command failed: {0}".format(err.strip()))

    try:
        download_file(server_ip, username, password, remote_tar, local_tar_path)
    finally:
        _ssh_exec(server_ip, username, password, "rm -f {0}".format(shell_quote(remote_tar)))

    logger.info("Directory tar download finished: %s", local_tar_path)
    return {"status": "success", "local_tar": local_tar_path}
