"""Aimotech / Quin command table used by the Ponek M100."""

from __future__ import annotations

from dataclasses import dataclass, field

GET = {
    "firmware": 0x07,
    "battery": 0x08,
    "serial": 0x09,
    "paper": 0x11,
    "cover": 0x12,
    "hot": 0x13,
    "label_type": 0x19,
    "bt_mac": 0x20,
    "chip_type": 0x38,
}

CONNECT_SWEEP = ("chip_type", "paper", "cover", "hot", "serial", "firmware", "battery", "label_type")

PAPER = {0x88: "empty", 0x89: "ok"}
COVER = {0x98: "closed", 0x99: "open"}
HOT = {0xA8: "ok", 0xA9: "overheated"}
LABEL = {0x0A: "gap", 0x0B: "continuous", 0x26: "black-mark", 0x4E: "other"}

PRINT_COMPLETE_TAG = 0x0F
PRINT_COMPLETE_PAYLOAD = 0x0C


def get_cmd(name: str) -> bytes:
    return bytes([0x1F, 0x11, GET[name]])


def parse_replies(buf: bytes) -> list[tuple[int, bytes]]:
    out: list[tuple[int, bytes]] = []
    i = 0
    known_len = {
        0x03: 1,
        0x04: 1,
        0x05: 1,
        0x06: 1,
        0x07: 3,
        0x08: 15,
        0x09: 1,
        0x0C: 1,
        0x0D: 12,
        0x0F: 1,
        0x17: 1,
        0x3B: 3,
    }
    while i < len(buf):
        if buf[i] != 0x1A:
            i += 1
            continue
        if i + 1 >= len(buf):
            break
        tag = buf[i + 1]
        rest = buf[i + 2 :]
        n = known_len.get(tag)
        if n is None:
            nxt = rest.find(b"\x1a")
            n = len(rest) if nxt < 0 else nxt
        n = min(n, len(rest))
        out.append((tag, rest[:n]))
        i += 2 + n
    return out


def _ascii(payload: bytes) -> str:
    return "".join(chr(c) if 32 <= c < 127 else "" for c in payload)


def _battery(payload: bytes) -> int | None:
    if not payload:
        return None
    b = payload[0]
    if b == 0x00:
        return 100
    if b in (0xA1, 0xA2, 0xA3, 0xA4):
        return {0xA1: 80, 0xA2: 50, 0xA3: 20, 0xA4: 0}[b]
    return int(b)


@dataclass
class PrinterStatus:
    serial: str | None = None
    firmware: str | None = None
    battery_percent: int | None = None
    paper: str | None = None
    cover: str | None = None
    hot: str | None = None
    label_type: str | None = None
    bt_mac: str | None = None
    print_complete: bool = False
    raw: list[tuple[int, bytes]] = field(default_factory=list)

    def apply(self, tag: int, payload: bytes) -> None:
        self.raw.append((tag, payload))
        if tag == 0x03 and payload:
            self.hot = HOT.get(payload[0], hex(payload[0]))
        elif tag == 0x04:
            self.battery_percent = _battery(payload)
        elif tag == 0x05 and payload:
            self.cover = COVER.get(payload[0], hex(payload[0]))
        elif tag == 0x06 and payload:
            self.paper = PAPER.get(payload[0], hex(payload[0]))
        elif tag == 0x07 and len(payload) >= 3:
            self.firmware = f"{payload[0]}.{payload[1]}.{payload[2]}"
        elif tag == 0x08:
            self.serial = _ascii(payload) or None
        elif tag == 0x0C and payload:
            self.label_type = LABEL.get(payload[0], hex(payload[0]))
        elif tag == 0x0D:
            self.bt_mac = _ascii(payload) or None
        elif tag == PRINT_COMPLETE_TAG:
            self.print_complete = bool(payload and payload[0] == PRINT_COMPLETE_PAYLOAD)


def status_from_bytes(buf: bytes, base: PrinterStatus | None = None) -> PrinterStatus:
    st = base or PrinterStatus()
    for tag, payload in parse_replies(buf):
        st.apply(tag, payload)
    return st
