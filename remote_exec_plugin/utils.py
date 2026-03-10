"""Utility helpers shared by plugin modules."""

from __future__ import annotations

import base64
import logging
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List


class PluginError(Exception):
    """Base exception for this project."""


class SharedStorageError(PluginError):
    """Errors for shared storage operations."""


class SecurityError(PluginError):
    """Errors for security policy violations."""


class UploadError(PluginError):
    """Errors for upload/download operations."""


class RemoteExecError(PluginError):
    """Errors for remote command execution."""


class ReportFetchError(PluginError):
    """Errors for report fetching."""


class ReportParseError(PluginError):
    """Errors for report parsing."""


def setup_logger(name: str) -> logging.Logger:
    """Create/reuse a logger configured for console output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def safe_mkdir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent_dir(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.parent


def b64_encode_file(path: str | Path) -> str:
    file_path = Path(path)
    with file_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_tar_gz(tar_path: str | Path, target_dir: str | Path) -> List[str]:
    tar_file = Path(tar_path)
    destination = safe_mkdir(target_dir)
    extracted: List[str] = []
    with tarfile.open(tar_file, "r:gz") as tar:
        tar.extractall(destination)
        for member in tar.getmembers():
            if member.isfile():
                extracted.append(str(destination / member.name))
    return extracted


def list_files_recursive(path: str | Path) -> List[str]:
    root = Path(path)
    if not root.exists():
        return []
    return [str(p) for p in root.rglob("*") if p.is_file()]


def timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
