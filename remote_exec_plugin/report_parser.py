"""Report parsing for JSON/XML/log artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

from utils import ReportParseError, list_files_recursive, setup_logger

logger = setup_logger(__name__)

_ERROR_TOKENS = ("error", "failed", "exception", "timeout")


def _parse_json(files: list[Path]) -> dict | None:
    for file in files:
        try:
            data = json.loads(file.read_text(encoding="utf-8", errors="replace"))
            if not isinstance(data, dict):
                return {
                    "job_status": "unknown",
                    "summary": f"JSON file '{file.name}' is not a dict.",
                    "key_metrics": {"file": file.name, "type": type(data).__name__},
                    "root_causes": [],
                    "artifacts": [str(file)],
                }

            status = data.get("status") or data.get("job_status") or "unknown"
            total = data.get("total", data.get("total_cases"))
            passed = data.get("passed")
            failed = data.get("failed")
            summary = data.get("summary") or f"Parsed JSON report: {file.name}"

            metrics = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "keys": list(data.keys()),
            }
            job_status = str(status).lower() if isinstance(status, str) else "unknown"
            if job_status not in {"success", "failed", "unknown"}:
                job_status = "unknown"

            return {
                "job_status": job_status,
                "summary": summary,
                "key_metrics": metrics,
                "root_causes": [],
                "artifacts": [str(file)],
            }
        except json.JSONDecodeError:
            continue
    return None


def _parse_xml(files: list[Path]) -> dict | None:
    for file in files:
        try:
            root = ET.parse(file).getroot()
            tests = int(root.attrib.get("tests", "0"))
            failures = int(root.attrib.get("failures", "0"))
            errors = int(root.attrib.get("errors", "0"))
            skipped = int(root.attrib.get("skipped", "0"))
            failed_total = failures + errors
            status = "failed" if failed_total > 0 else "success"
            summary = (
                f"JUnit XML parsed: tests={tests}, failures={failures}, "
                f"errors={errors}, skipped={skipped}"
            )
            return {
                "job_status": status,
                "summary": summary,
                "key_metrics": {
                    "tests": tests,
                    "failures": failures,
                    "errors": errors,
                    "skipped": skipped,
                },
                "root_causes": [],
                "artifacts": [str(file)],
            }
        except ET.ParseError:
            continue
        except Exception:
            continue
    return None


def _parse_logs(files: list[Path]) -> dict | None:
    if not files:
        return None

    matched_lines: list[str] = []
    artifacts: list[str] = []
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in content:
                lower = line.lower()
                if any(token in lower for token in _ERROR_TOKENS):
                    matched_lines.append(f"{file.name}: {line.strip()}")
            artifacts.append(str(file))
        except Exception:
            continue

    if not artifacts:
        return None

    summary = f"Scanned {len(artifacts)} log/text files, found {len(matched_lines)} suspicious lines."
    status = "failed" if matched_lines else "unknown"
    return {
        "job_status": status,
        "summary": summary,
        "key_metrics": {
            "log_files": len(artifacts),
            "error_lines": len(matched_lines),
        },
        "root_causes": matched_lines[:10],
        "artifacts": artifacts,
    }


def analyze_report(report_path: str) -> dict:
    logger.info("Analyzing report path: %s", report_path)
    path = Path(report_path)
    if not path.exists():
        return {
            "job_status": "unknown",
            "summary": f"Report path does not exist: {report_path}",
            "key_metrics": {},
            "root_causes": ["Report path not found"],
            "artifacts": [],
        }

    files = [Path(p) for p in list_files_recursive(path)] if path.is_dir() else [path]
    json_files = [f for f in files if f.suffix.lower() == ".json"]
    xml_files = [f for f in files if f.suffix.lower() == ".xml"]
    log_files = [f for f in files if f.suffix.lower() in {".log", ".txt"}]

    try:
        return (
            _parse_json(json_files)
            or _parse_xml(xml_files)
            or _parse_logs(log_files)
            or {
                "job_status": "unknown",
                "summary": "No supported report files detected.",
                "key_metrics": {"file_count": len(files)},
                "root_causes": [],
                "artifacts": [str(f) for f in files],
            }
        )
    except Exception as exc:
        raise ReportParseError(f"Failed to analyze report: {exc}") from exc
