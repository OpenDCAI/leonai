import http.server
import socket
import socketserver
import subprocess
import threading
from pathlib import Path

SCRIPT_PATH = Path("scripts/path_a_tunnel_preflight.sh")


class _StatusHandler(http.server.BaseHTTPRequestHandler):
    status_code = 200

    def do_GET(self) -> None:
        self.send_response(self.status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args: object) -> None:
        return


class _ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _start_http_server(status_code: int) -> tuple[_ThreadedHTTPServer, int]:
    handler_cls = type("DynamicStatusHandler", (_StatusHandler,), {"status_code": status_code})
    server = _ThreadedHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_port


def _run_preflight(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_creds(tmp_path: Path) -> Path:
    credential_file = tmp_path / "creds.txt"
    credential_file.write_text("token=demo\n", encoding="utf-8")
    return credential_file


def test_fails_loud_when_required_args_missing() -> None:
    result = _run_preflight()

    assert result.returncode == 1
    assert "--host is required" in result.stdout


def test_fails_loud_when_credentials_file_missing(tmp_path: Path) -> None:
    server, port = _start_http_server(status_code=200)
    try:
        missing_file = tmp_path / "missing_creds.txt"
        result = _run_preflight(
            "--host",
            "localhost",
            "--port",
            str(port),
            "--ingress-url",
            f"http://127.0.0.1:{port}/health",
            "--credential-file",
            str(missing_file),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert result.returncode == 1
    assert "credential file not readable" in result.stdout


def test_fails_loud_on_ingress_mapping_mismatch_status(tmp_path: Path) -> None:
    server, port = _start_http_server(status_code=404)
    creds = _write_creds(tmp_path)
    try:
        result = _run_preflight(
            "--host",
            "localhost",
            "--port",
            str(port),
            "--ingress-url",
            f"http://127.0.0.1:{port}/health",
            "--credential-file",
            str(creds),
        )
    finally:
        server.shutdown()
        server.server_close()

    assert result.returncode == 1
    assert "unexpected ingress status: 404" in result.stdout


def test_fails_loud_on_non_listening_port(tmp_path: Path) -> None:
    creds = _write_creds(tmp_path)

    # @@@tcp-refused-port - bind a port without listen() so connect must fail deterministically.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as port_holder:
        port_holder.bind(("127.0.0.1", 0))
        closed_port = port_holder.getsockname()[1]
        result = _run_preflight(
            "--host",
            "localhost",
            "--port",
            str(closed_port),
            "--ingress-url",
            "http://127.0.0.1:9/health",
            "--credential-file",
            str(creds),
        )

    assert result.returncode == 1
    assert f"tcp connection failed to localhost:{closed_port}" in result.stdout


def test_passes_when_all_checks_are_satisfied(tmp_path: Path) -> None:
    server, port = _start_http_server(status_code=200)
    creds = _write_creds(tmp_path)
    try:
        result = _run_preflight(
            "--host",
            "localhost",
            "--port",
            str(port),
            "--ingress-url",
            f"http://127.0.0.1:{port}/health",
            "--credential-file",
            str(creds),
        )
    finally:
        # @@@server-teardown-order - shutdown before close avoids dangling serve_forever thread.
        server.shutdown()
        server.server_close()

    assert result.returncode == 0
    assert "preflight passed for route switch" in result.stdout
