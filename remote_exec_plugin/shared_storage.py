"""Shared storage access layer with strict path safety checks."""

from __future__ import annotations

import shutil
from pathlib import Path

from config import ARCHIVE_DIR, FAILED_DIR, MAX_FILE_SIZE, OUTBOX_DIR, REPORTS_DIR, SHARED_ROOT
from utils import SharedStorageError, SecurityError, b64_encode_file, safe_mkdir, setup_logger

logger = setup_logger(__name__)


def _ensure_under_shared_root(path: Path) -> Path:
    try:
        path.resolve().relative_to(SHARED_ROOT.resolve())
    except ValueError as exc:
        raise SecurityError(f"Path '{path}' is outside shared root '{SHARED_ROOT}'.") from exc
    return path


def resolve_shared_path(file_key: str) -> str:
    if not file_key or file_key.startswith("/"):
        raise SharedStorageError("file_key must be a non-empty relative path.")
    target = _ensure_under_shared_root(SHARED_ROOT / file_key)
    if ".." in Path(file_key).parts:
        raise SecurityError("Path traversal is not allowed in file_key.")
    return str(target)


def ensure_shared_dirs() -> None:
    for directory in (OUTBOX_DIR, REPORTS_DIR, ARCHIVE_DIR, FAILED_DIR):
        safe_mkdir(directory)


def read_shared_file(file_key: str) -> dict:
    logger.info("Start reading shared file: %s", file_key)
    full_path = Path(resolve_shared_path(file_key))

    if not full_path.exists() or not full_path.is_file():
        raise SharedStorageError(f"Shared file not found: {file_key}")

    size = full_path.stat().st_size
    if size > MAX_FILE_SIZE:
        raise SharedStorageError(
            f"File '{file_key}' is too large ({size} bytes), limit={MAX_FILE_SIZE}."
        )

    result = {
        "file_name": full_path.name,
        "full_path": str(full_path),
        "size": size,
        "content_base64": b64_encode_file(full_path),
    }
    logger.info("Finished reading shared file: %s", file_key)
    return result


def _move_file(file_key: str, target_root: Path) -> str:
    source = Path(resolve_shared_path(file_key))
    if not source.exists() or not source.is_file():
        raise SharedStorageError(f"Source file not found: {file_key}")

    relative = source.resolve().relative_to(SHARED_ROOT.resolve())
    target = _ensure_under_shared_root(target_root / relative.name)
    safe_mkdir(target.parent)
    shutil.move(str(source), str(target))
    return str(target)


def move_to_archive(file_key: str) -> str:
    logger.info("Moving file to archive: %s", file_key)
    return _move_file(file_key, ARCHIVE_DIR)


def move_to_failed(file_key: str) -> str:
    logger.info("Moving file to failed: %s", file_key)
    return _move_file(file_key, FAILED_DIR)
