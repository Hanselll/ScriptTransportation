"""Utility helpers shared by plugin modules."""


import base64
import logging
import os
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class PluginError(Exception):
    """Base exception for this project."""


class SharedStorageError(PluginError):
    pass


class SecurityError(PluginError):
    pass


class UploadError(PluginError):
    pass


class RemoteExecError(PluginError):
    pass


class ReportFetchError(PluginError):
    pass


class ReportParseError(PluginError):
    pass


def setup_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def safe_mkdir(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent_dir(path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p.parent


def b64_encode_file(path):
    file_path = Path(path)
    with file_path.open("rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def extract_tar_gz(tar_path, target_dir):
    tar_file = Path(tar_path)
    destination = safe_mkdir(target_dir)
    extracted = []
    with tarfile.open(str(tar_file), "r:gz") as tf:
        tf.extractall(str(destination))
        for member in tf.getmembers():
            if member.isfile():
                extracted.append(str(destination / member.name))
    return extracted


def list_files_recursive(path):
    root = Path(path)
    if not root.exists():
        return []
    return [str(p) for p in root.rglob("*") if p.is_file()]


def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def require_command(cmd_name):
    if shutil.which(cmd_name) is None:
        raise PluginError("Required command not found: {0}".format(cmd_name))


def run_cmd(cmd, timeout=None):
    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        universal_newlines=True,
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def shell_quote(value):
    return "'" + str(value).replace("'", "'\\''") + "'"
