"""SSH command execution module."""


from config import is_allowed_host, is_command_safe
from utils import RemoteExecError, SecurityError, require_command, run_cmd, setup_logger

logger = setup_logger(__name__)


def run_remote_command(server_ip, username, password, command, timeout=600):
    if not is_allowed_host(server_ip):
        raise SecurityError("Server '{0}' is not in ALLOWED_HOSTS.".format(server_ip))
    if not is_command_safe(command):
        raise SecurityError("Command rejected by safety policy.")

    require_command("ssh")
    require_command("sshpass")
    logger.info("Running remote command on %s: %s", server_ip, command)

    cmd = [
        "sshpass",
        "-p",
        password,
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "{0}@{1}".format(username, server_ip),
        command,
    ]

    try:
        code, out, err = run_cmd(cmd, timeout=timeout)
        return {"exit_code": code, "stdout": out, "stderr": err, "command": command}
    except Exception as exc:
        raise RemoteExecError("Remote execution error: {0}".format(exc))
