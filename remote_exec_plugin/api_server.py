"""Persistent HTTP API server exposing remote_exec_plugin tool functions."""

import argparse
import base64
import cgi
import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from tools import (
    tool_analyze_report,
    tool_fetch_report,
    tool_read_shared_file,
    tool_run_full_job,
    tool_run_remote_command,
    tool_upload_file,
    tool_upload_file_content,
)
from utils import setup_logger

logger = setup_logger(__name__)


TOOL_SPECS = {
    "/tool/read_shared_file": {
        "func": tool_read_shared_file,
        "args": ["file_key"],
        "optional_args": [],
    },
    "/tool/upload_file": {
        "func": tool_upload_file,
        "args": ["file_key", "server_ip", "username", "password", "remote_path"],
        "optional_args": ["ssh_port"],
    },
    "/tool/upload_file_content": {
        "func": tool_upload_file_content,
        "args": ["file_name", "content_base64", "server_ip", "username", "password", "remote_path"],
        "optional_args": ["ssh_port"],
    },
    "/tool/run_remote_command": {
        "func": tool_run_remote_command,
        "args": ["server_ip", "username", "password", "command"],
        "optional_args": ["ssh_port"],
    },
    "/tool/fetch_report": {
        "func": tool_fetch_report,
        "args": ["server_ip", "username", "password", "remote_report_path", "local_report_key"],
        "optional_args": ["ssh_port"],
    },
    "/tool/analyze_report": {
        "func": tool_analyze_report,
        "args": ["report_path"],
        "optional_args": [],
    },
    "/tool/run_full_job": {
        "func": tool_run_full_job,
        "args": [
            "file_key",
            "server_ip",
            "username",
            "password",
            "remote_path",
            "run_command",
            "remote_report_path",
            "local_report_key",
        ],
        "optional_args": ["ssh_port"],
    },
}


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "remote_exec_plugin_api/1.0"

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError(
                "Request body is not valid JSON. Hint: check commas in JSON and use single-quoted -d or heredoc."
            )

    def _normalize_payload(self, path, payload):
        """Backward-compatible field aliases for simpler caller payloads."""
        if path == "/tool/upload_file":
            # allow file_name as alias of file_key
            if "file_key" not in payload and "file_name" in payload:
                payload["file_key"] = payload.get("file_name")
        return payload

    def _handle_upload_file_multipart(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )

        file_item = form.getfirst("file")
        if "file" in form and getattr(form["file"], "file", None):
            file_field = form["file"]
            file_name = file_field.filename or "upload.bin"
            file_bytes = file_field.file.read()
        elif "file_name" in form and getattr(form["file_name"], "file", None):
            file_field = form["file_name"]
            file_name = file_field.filename or "upload.bin"
            file_bytes = file_field.file.read()
        else:
            raise ValueError("multipart upload requires file field: use -F 'file=@/path/to/local.file'")

        server_ip = form.getfirst("server_ip")
        username = form.getfirst("username")
        password = form.getfirst("password")
        remote_path = form.getfirst("remote_path")
        ssh_port = form.getfirst("ssh_port")

        missing = []
        if not server_ip:
            missing.append("server_ip")
        if not username:
            missing.append("username")
        if not password:
            missing.append("password")
        if not remote_path:
            missing.append("remote_path")
        if missing:
            raise ValueError("Missing required fields: {0}".format(", ".join(missing)))

        kwargs = {
            "file_name": file_name,
            "content_base64": base64.b64encode(file_bytes).decode("utf-8"),
            "server_ip": server_ip,
            "username": username,
            "password": password,
            "remote_path": remote_path,
        }
        if ssh_port:
            kwargs["ssh_port"] = int(ssh_port)

        return tool_upload_file_content(**kwargs)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if self.path == "/tools":
            self._send_json(200, {"tools": sorted(TOOL_SPECS.keys())})
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path not in TOOL_SPECS:
            self._send_json(404, {"error": "Not found"})
            return

        try:
            content_type = self.headers.get("Content-Type", "")
            if self.path == "/tool/upload_file" and content_type.startswith("multipart/form-data"):
                logger.info("API call %s (multipart)", self.path)
                result = self._handle_upload_file_multipart()
                self._send_json(200, {"status": "success", "result": result})
                return

            payload = self._normalize_payload(self.path, self._read_json())
            spec = TOOL_SPECS[self.path]
            missing = [name for name in spec["args"] if name not in payload]
            if missing:
                self._send_json(400, {"error": "Missing required fields", "missing": missing})
                return

            kwargs = {}
            for name in spec["args"]:
                kwargs[name] = payload.get(name)
            for name in spec.get("optional_args", []):
                if name in payload and payload.get(name) is not None:
                    kwargs[name] = payload.get(name)

            logger.info("API call %s", self.path)
            result = spec["func"](**kwargs)
            self._send_json(200, {"status": "success", "result": result})
        except ValueError as exc:
            self._send_json(400, {"status": "error", "error": str(exc)})
        except Exception as exc:
            logger.error("API call failed: %s\n%s", exc, traceback.format_exc())
            self._send_json(500, {"status": "error", "error": str(exc)})

    def log_message(self, fmt, *args):
        logger.info("%s - %s", self.address_string(), fmt % args)


def run_server(host, port):
    server = ThreadingHTTPServer((host, port), ApiHandler)
    logger.info("remote_exec_plugin API server started on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run remote_exec_plugin HTTP API server")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host, default: 0.0.0.0")
    parser.add_argument("--port", type=int, default=8080, help="Listen port, default: 8080")
    args = parser.parse_args()
    run_server(args.host, args.port)
