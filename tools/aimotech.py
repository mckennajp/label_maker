"""Aimotech / Quin command helpers shared by the probe tools."""

from __future__ import annotations

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

# Official Print Master connect sweep, in the order the SDK fires it.
CONNECT_SWEEP = ("chip_type", "paper", "cover", "hot", "serial", "firmware", "battery")

PAPER = {0x88: "empty", 0x89: "ok"}
COVER = {0x98: "closed", 0x99: "open"}
HOT = {0xA8: "ok", 0xA9: "overheated"}
LABEL = {0x0A: "gap", 0x0B: "continuous", 0x26: "black-mark", 0x4E: "other"}
BATTERY_MARK = {0x00: "full (firmware quirk)", 0xA1: "high", 0xA2: "med", 0xA3: "low", 0xA4: "fault"}


def get_cmd(name: str) -> bytes:
    return bytes([0x1F, 0x11, GET[name]])


def sweep_bytes(names: tuple[str, ...] = CONNECT_SWEEP) -> bytes:
    return b"".join(get_cmd(n) for n in names)


def parse_replies(buf: bytes) -> list[tuple[int, bytes, str]]:
    """Split a 1A-prefixed stream into (tag, payload, description)."""
    out: list[tuple[int, bytes, str]] = []
    i = 0
    while i < len(buf):
        if buf[i] != 0x1A:
            i += 1
            continue
        if i + 1 >= len(buf):
            break
        tag = buf[i + 1]
        payload, consumed, desc = _payload_for_tag(tag, buf[i + 2 :])
        out.append((tag, payload, desc))
        i += 2 + consumed
    return out


def _payload_for_tag(tag: int, rest: bytes) -> tuple[bytes, int, str]:
    # Most status replies are a fixed 1–15 bytes. We take a conservative
    # slice: stop at the next 0x1A that looks like a new tag, otherwise
    # use the known length for this tag.
    known_len = {
        0x03: 1,  # hot
        0x04: 1,  # battery
        0x05: 1,  # cover
        0x06: 1,  # paper
        0x07: 3,  # firmware
        0x08: 15,  # serial
        0x09: 1,  # auto-power
        0x0C: 1,  # label type (tag 12)
        0x3B: 3,  # chip type
    }
    n = known_len.get(tag)
    if n is None:
        nxt = rest.find(b"\x1a")
        n = len(rest) if nxt < 0 else nxt
    n = min(n, len(rest))
    payload = rest[:n]
    return payload, n, describe(tag, payload)


def describe(tag: int, payload: bytes) -> str:
    if tag == 0x03 and payload:
        return f"hot={HOT.get(payload[0], hex(payload[0]))}"
    if tag == 0x04 and payload:
        b = payload[0]
        extra = BATTERY_MARK.get(b)
        return f"battery={extra or f'{b}%'}"
    if tag == 0x05 and payload:
        return f"cover={COVER.get(payload[0], hex(payload[0]))}"
    if tag == 0x06 and payload:
        return f"paper={PAPER.get(payload[0], hex(payload[0]))}"
    if tag == 0x07 and len(payload) >= 3:
        return f"firmware={payload[0]}.{payload[1]}.{payload[2]}"
    if tag == 0x08:
        sn = "".join(chr(c) if 32 <= c < 127 else "." for c in payload)
        return f"serial={sn!r}"
    if tag == 0x0C and payload:
        return f"label_type={LABEL.get(payload[0], hex(payload[0]))}"
    if tag == 0x3B and payload:
        flags = " ".join(f"{b:08b}" for b in payload)
        return f"chip_type bytes={payload.hex()} bits={flags}"
    return f"tag=0x{tag:02x} payload={payload.hex() or '—'}"


def hexdump(data: bytes, prefix: str = "") -> str:
    if not data:
        return f"{prefix}(empty)"
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off : off + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{prefix}{off:04x}  {hexpart:<48s}  {ascii_part}")
    return "\n".join(lines)


NIIMBOT_HINT = bytes([0x55, 0x55])
CATPRINTER_HINT = bytes([0x51, 0x78])


def family_guess(rx: bytes) -> str | None:
    if not rx:
        return None
    if rx.startswith(b"\x1a") or b"\x1a" in rx[:8]:
        return "Aimotech/Quin (1A-tagged replies) — expected family"
    if NIIMBOT_HINT in rx[:16]:
        return "Looks like NIIMBOT framing (55 55). Unexpected — tell the agent."
    if CATPRINTER_HINT in rx[:8]:
        return "Looks like cat-printer 51 78 framing. Unexpected."
    return None
