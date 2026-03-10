"""Report parsing for JSON/XML/log artifacts."""


import json
import xml.etree.ElementTree as ET
from pathlib import Path

from utils import ReportParseError, list_files_recursive, setup_logger

logger = setup_logger(__name__)
_ERROR_TOKENS = ("error", "failed", "exception", "timeout")


def _parse_json(files):
    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue

        if not isinstance(data, dict):
            return {
                "job_status": "unknown",
                "summary": "JSON file '{0}' is not a dict.".format(file_path.name),
                "key_metrics": {"file": file_path.name, "top_level_type": type(data).__name__},
                "root_causes": [],
                "artifacts": [str(file_path)],
            }

        status = data.get("status") or data.get("job_status") or "unknown"
        total = data.get("total", data.get("total_cases"))
        return {
            "job_status": status if status in ("success", "failed", "unknown") else "unknown",
            "summary": data.get("summary") or "Parsed JSON report: {0}".format(file_path.name),
            "key_metrics": {
                "total": total,
                "passed": data.get("passed"),
                "failed": data.get("failed"),
                "keys": sorted(list(data.keys())),
            },
            "root_causes": [],
            "artifacts": [str(file_path)],
        }
    return None


def _parse_xml(files):
    for file_path in files:
        try:
            root = ET.parse(str(file_path)).getroot()
            tests = int(root.attrib.get("tests", "0"))
            failures = int(root.attrib.get("failures", "0"))
            errors = int(root.attrib.get("errors", "0"))
            skipped = int(root.attrib.get("skipped", "0"))
            return {
                "job_status": "failed" if (failures + errors) > 0 else "success",
                "summary": "JUnit XML parsed: tests={0}, failures={1}, errors={2}, skipped={3}".format(
                    tests, failures, errors, skipped
                ),
                "key_metrics": {
                    "tests": tests,
                    "failures": failures,
                    "errors": errors,
                    "skipped": skipped,
                },
                "root_causes": [],
                "artifacts": [str(file_path)],
            }
        except Exception:
            continue
    return None


def _parse_logs(files):
    if not files:
        return None
    matched = []
    artifacts = []
    for file_path in files:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines:
                lower = line.lower()
                if any(token in lower for token in _ERROR_TOKENS):
                    matched.append("{0}: {1}".format(file_path.name, line.strip()))
            artifacts.append(str(file_path))
        except Exception:
            continue

    if not artifacts:
        return None
    return {
        "job_status": "failed" if matched else "unknown",
        "summary": "Scanned {0} log/text files, found {1} suspicious lines.".format(len(artifacts), len(matched)),
        "key_metrics": {"log_files": len(artifacts), "error_lines": len(matched)},
        "root_causes": matched[:10],
        "artifacts": artifacts,
    }


def analyze_report(report_path):
    logger.info("Analyzing report path: %s", report_path)
    path = Path(report_path)
    if not path.exists():
        return {
            "job_status": "unknown",
            "summary": "Report path does not exist: {0}".format(report_path),
            "key_metrics": {},
            "root_causes": ["Report path not found"],
            "artifacts": [],
        }

    files = [Path(p) for p in list_files_recursive(path)] if path.is_dir() else [path]
    json_files = [f for f in files if f.suffix.lower() == ".json"]
    xml_files = [f for f in files if f.suffix.lower() == ".xml"]
    log_files = [f for f in files if f.suffix.lower() in (".log", ".txt")]

    try:
        return _parse_json(json_files) or _parse_xml(xml_files) or _parse_logs(log_files) or {
            "job_status": "unknown",
            "summary": "No supported report files detected.",
            "key_metrics": {"file_count": len(files)},
            "root_causes": [],
            "artifacts": [str(f) for f in files],
        }
    except Exception as exc:
        raise ReportParseError("Failed to analyze report: {0}".format(exc))
