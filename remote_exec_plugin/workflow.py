"""Main workflow orchestration module."""


from report_fetcher import fetch_report
from report_parser import analyze_report
from sftp_transfer import upload_file
from shared_storage import ensure_shared_dirs, move_to_archive, move_to_failed, read_shared_file, resolve_shared_path
from ssh_executor import run_remote_command
from utils import setup_logger

logger = setup_logger(__name__)


def deploy_and_run(file_key, server_ip, username, password, remote_path, run_command):
    ensure_shared_dirs()
    file_info = read_shared_file(file_key)
    local_path = resolve_shared_path(file_key)
    upload_result = upload_file(local_path, server_ip, username, password, remote_path)
    exec_result = run_remote_command(server_ip, username, password, run_command)
    return {"file": file_info, "upload": upload_result, "execution": exec_result}


def fetch_and_analyze(server_ip, username, password, remote_report_path, local_report_key):
    fetch_result = fetch_report(server_ip, username, password, remote_report_path, local_report_key)
    analysis = analyze_report(fetch_result["local_report_dir"])
    return {"report": fetch_result, "analysis": analysis}


def run_full_job(file_key, server_ip, username, password, remote_path, run_command, remote_report_path, local_report_key):
    job_status = "failed"
    execution = {}
    report = {"local_report_dir": "", "artifacts": []}
    analysis = {"job_status": "unknown", "summary": "analysis not run", "key_metrics": {}, "root_causes": []}

    try:
        deploy_result = deploy_and_run(file_key, server_ip, username, password, remote_path, run_command)
        execution = deploy_result["execution"]
        try:
            fetched = fetch_and_analyze(server_ip, username, password, remote_report_path, local_report_key)
            report = fetched["report"]
            analysis = fetched["analysis"]
        except Exception as report_exc:
            logger.exception("Failed to fetch/analyze report: %s", report_exc)
            analysis = {
                "job_status": "unknown",
                "summary": "report stage failed: {0}".format(report_exc),
                "key_metrics": {},
                "root_causes": [str(report_exc)],
            }

        if execution.get("exit_code", 1) == 0 and analysis.get("job_status") != "failed":
            job_status = "success"
            move_to_archive(file_key)
        else:
            move_to_failed(file_key)
    except Exception as exc:
        logger.exception("run_full_job failed: %s", exc)
        execution = {"exit_code": -1, "stdout": "", "stderr": str(exc), "command": run_command}
        try:
            fetched = fetch_and_analyze(server_ip, username, password, remote_report_path, local_report_key)
            report = fetched["report"]
            analysis = fetched["analysis"]
        except Exception as report_exc:
            logger.exception("Report fetch after failure also failed: %s", report_exc)
            analysis = {
                "job_status": "unknown",
                "summary": "report stage failed: {0}".format(report_exc),
                "key_metrics": {},
                "root_causes": [str(report_exc)],
            }
        try:
            move_to_failed(file_key)
        except Exception:
            logger.exception("Failed to move file to failed archive")

    return {
        "job_status": job_status,
        "file_key": file_key,
        "server_ip": server_ip,
        "remote_path": remote_path,
        "run_command": run_command,
        "execution": execution,
        "report": {"local_report_dir": report.get("local_report_dir", ""), "artifacts": report.get("artifacts", [])},
        "analysis": {
            "job_status": analysis.get("job_status", "unknown"),
            "summary": analysis.get("summary", ""),
            "key_metrics": analysis.get("key_metrics", {}),
            "root_causes": analysis.get("root_causes", []),
        },
    }
