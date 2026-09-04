"""Local designer + print API backed by M100Client."""

from __future__ import annotations

import json
import ssl
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

from m100.client import M100Client
from m100.protocol import PrinterStatus

STATIC = Path(__file__).resolve().parent / "static"


def _status_json(st: PrinterStatus, connected: bool, error: str | None = None) -> dict:
    return {
        "connected": connected,
        "serial": st.serial,
        "firmware": st.firmware,
        "battery_percent": st.battery_percent,
        "paper": st.paper,
        "cover": st.cover,
        "hot": st.hot,
        "label_type": st.label_type,
        "print_complete": st.print_complete,
        "error": error,
    }


class DesignerHandler(SimpleHTTPRequestHandler):
    printer: M100Client | None
    lock: threading.Lock

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"  http  {self.address_string()}  {fmt % args}")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            self._handle_status()
            return
        if path in ("/", "/index.html"):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/print":
            self._handle_print()
            return
        self.send_error(404)

    def end_headers(self) -> None:
        if self.path.endswith((".js", ".css", ".html")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _handle_status(self) -> None:
        if self.printer is None:
            self._json(200, _status_json(PrinterStatus(), False, "browser bluetooth"))
            return
        with self.lock:
            try:
                if not self.printer.connected:
                    self.printer.connect()
                st = self.printer.status()
                self._json(200, _status_json(st, True))
            except Exception as e:
                self._json(200, _status_json(PrinterStatus(), False, str(e)))

    def _handle_print(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            self._json(400, {"ok": False, "error": "empty body"})
            return
        qs = parse_qs(urlparse(self.path).query)
        copies = int((qs.get("copies") or ["1"])[0])
        copies = max(1, min(copies, 20))
        def _mm(name, default):
            try:
                return float((qs.get(name) or [str(default)])[0])
            except ValueError:
                return default
        width_mm = _mm("width_mm", 40.0)
        height_mm = _mm("height_mm", 30.0)
        try:
            image = Image.open(BytesIO(raw)).convert("RGB")
        except Exception as e:
            self._json(400, {"ok": False, "error": f"not an image: {e}"})
            return
        if self.printer is None:
            self._json(400, {"ok": False, "error": "Connect Bluetooth in the page (no COM port on the server)"})
            return
        with self.lock:
            try:
                if not self.printer.connected:
                    self.printer.connect()
                st = self.printer.print_image(
                    image, copies=copies, width_mm=width_mm, height_mm=height_mm
                )
                self._json(200, {**_status_json(st, True), "ok": True})
            except Exception as e:
                self._json(500, {"ok": False, "error": str(e)})


def serve(
    com_port: str | None = None,
    http_port: int = 8765,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    https: bool = False,
) -> None:
    printer = None
    if com_port:
        printer = M100Client(com_port)
        try:
            printer.connect()
            print(f"printer  {com_port}  {printer.last_status.serial}  fw {printer.last_status.firmware}")
        except Exception as e:
            print(f"printer  {com_port}  not connected yet ({e}) — use browser Bluetooth")
    else:
        print("printer  browser Bluetooth (phone) / Web Serial (desktop)")

    lock = threading.Lock()

    class Bound(DesignerHandler):
        pass

    Bound.printer = printer
    Bound.lock = lock

    httpd = ThreadingHTTPServer((host, http_port), Bound)
    scheme = "http"
    if https:
        from m100.certs import ensure_certs, lan_ip

        cert, key = ensure_certs(Path(__file__).resolve().parents[2] / ".certs")
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
        print(f"tls      {cert}")
        print("         Phone browsers need HTTPS for Web Bluetooth.")
        print("         Accept the certificate warning once.")

    from m100.certs import lan_ip

    print(f"designer {scheme}://127.0.0.1:{http_port}/")
    if host in ("0.0.0.0", "::"):
        print(f"phone    {scheme}://{lan_ip()}:{http_port}/")
        print("         Same Wi-Fi as this PC. Android Chrome only (not iPhone Safari).")
        print("         Allow Bluetooth when Chrome asks.")
    print("Ctrl+C to stop")
    if open_browser:
        webbrowser.open(f"{scheme}://127.0.0.1:{http_port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        httpd.server_close()
        if printer is not None:
            printer.close()
