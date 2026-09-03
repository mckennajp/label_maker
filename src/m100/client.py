"""Serial client for the Ponek M100 (Aimotech SPP)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from m100.protocol import CONNECT_SWEEP, PRINT_COMPLETE_TAG, PrinterStatus, get_cmd, status_from_bytes
from m100.raster import (
    DEFAULT_DENSITY,
    DEFAULT_SPEED,
    Geometry,
    encode_job,
    fit_to_label,
)

if TYPE_CHECKING:
    from PIL import Image

try:
    import serial
except ImportError as e:  # pragma: no cover
    raise SystemExit("pip install pyserial pillow") from e


class M100Client:
    """Talk to a Ponek M100 over a Windows COM port (Bluetooth SPP or USB CDC).

    Calibration (40×30 mm gap stock on this unit): 384 px head, 3.5 mm
    right shift, 0 top pad. Keep the port open until the printer ACKs
    `1A 0F 0C` or the hold timeout fires — closing early aborts the job.
    """

    def __init__(
        self,
        port: str,
        baud: int = 115200,
        geometry: Geometry | None = None,
        speed: int = DEFAULT_SPEED,
        density: int = DEFAULT_DENSITY,
        chunk: int = 256,
        pace_ms: float = 20.0,
        hold: float = 12.0,
    ) -> None:
        self.port = port
        self.baud = baud
        self.geometry = geometry or Geometry()
        self.speed = speed
        self.density = density
        self.chunk = chunk
        self.pace_s = pace_ms / 1000.0
        self.hold = hold
        self._ser: serial.Serial | None = None
        self.last_status = PrinterStatus()

    @property
    def connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def connect(self) -> PrinterStatus:
        if self.connected:
            return self.status()
        self._ser = serial.Serial(
            self.port,
            baudrate=self.baud,
            timeout=0.1,
            write_timeout=10,
        )
        leftover = self._ser.read(1024)
        if leftover:
            status_from_bytes(leftover, self.last_status)
        return self.status()

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def __enter__(self) -> M100Client:
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _require(self) -> serial.Serial:
        if not self.connected:
            raise RuntimeError("not connected — call connect() first")
        assert self._ser is not None
        return self._ser

    def _transact(self, payload: bytes, wait: float) -> bytes:
        ser = self._require()
        ser.reset_input_buffer()
        ser.write(payload)
        ser.flush()
        deadline = time.time() + wait
        buf = bytearray()
        while time.time() < deadline:
            chunk = ser.read(256)
            if chunk:
                buf.extend(chunk)
                time.sleep(0.05)
                continue
            if buf:
                break
            time.sleep(0.02)
        return bytes(buf)

    def query(self, *names: str, wait: float = 0.8) -> PrinterStatus:
        if not names:
            names = CONNECT_SWEEP
        for name in names:
            rx = self._transact(get_cmd(name), wait)
            status_from_bytes(rx, self.last_status)
        return self.last_status

    def status(self) -> PrinterStatus:
        return self.query(*CONNECT_SWEEP)

    def _write_paced(self, payload: bytes) -> None:
        ser = self._require()
        sent = 0
        while sent < len(payload):
            n = ser.write(payload[sent : sent + self.chunk])
            ser.flush()
            sent += n
            if sent < len(payload) and self.pace_s:
                time.sleep(self.pace_s)

    def _wait_complete(self) -> PrinterStatus:
        ser = self._require()
        deadline = time.time() + self.hold
        while time.time() < deadline:
            chunk = ser.read(256)
            if chunk:
                status_from_bytes(chunk, self.last_status)
                if self.last_status.print_complete:
                    return self.last_status
            else:
                time.sleep(0.15)
        return self.last_status

    def print_page(self, page: Image.Image) -> PrinterStatus:
        """Send an already-laid-out 1-bpp page (full head width)."""
        self.last_status.print_complete = False
        job = encode_job(page, speed=self.speed, density=self.density)
        self._write_paced(job)
        return self._wait_complete()

    def print_image(
        self,
        image: Image.Image,
        width_mm: float | None = None,
        height_mm: float | None = None,
        copies: int = 1,
    ) -> PrinterStatus:
        """Fit a PIL image onto the label and print. Dark pixels burn."""
        geo = self.geometry
        if width_mm is not None or height_mm is not None:
            geo = Geometry(
                label_w_mm=width_mm if width_mm is not None else geo.label_w_mm,
                label_h_mm=height_mm if height_mm is not None else geo.label_h_mm,
                head_px=geo.head_px,
                shift_right_mm=geo.shift_right_mm,
                pad_top_mm=geo.pad_top_mm,
            )
        page = fit_to_label(image, geo)
        last = self.last_status
        for i in range(max(1, copies)):
            last = self.print_page(page)
            if i + 1 < copies:
                time.sleep(0.4)
                self.last_status.print_complete = False
        return last

    def print_file(self, path: str | Path, **kwargs) -> PrinterStatus:
        from PIL import Image

        with Image.open(path) as im:
            return self.print_image(im.copy(), **kwargs)
