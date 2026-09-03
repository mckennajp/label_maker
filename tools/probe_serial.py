"""Send the Aimotech identification sweep over a serial/COM port.

Works for USB CDC and for a Classic Bluetooth SPP port that Windows
already assigned (pair the printer in Settings first).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aimotech import (  # noqa: E402
    CONNECT_SWEEP,
    family_guess,
    get_cmd,
    hexdump,
    parse_replies,
    sweep_bytes,
)


def open_serial(port: str, baud: int, timeout: float):
    try:
        import serial
    except ImportError as e:
        raise SystemExit("pip install pyserial") from e
    return serial.Serial(port, baudrate=baud, timeout=timeout, write_timeout=2)


def transact(ser, payload: bytes, wait: float) -> bytes:
    ser.reset_input_buffer()
    ser.write(payload)
    ser.flush()
    deadline = time.time() + wait
    buf = bytearray()
    while time.time() < deadline:
        chunk = ser.read(256)
        if chunk:
            buf.extend(chunk)
            # keep reading a little after the last byte so coalesced
            # replies arrive together
            time.sleep(0.05)
            continue
        if buf:
            break
        time.sleep(0.02)
    return bytes(buf)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("port", help="COMx on Windows, /dev/tty* elsewhere")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--wait", type=float, default=1.0, help="seconds to wait per command")
    p.add_argument(
        "--one-shot",
        action="store_true",
        help="send the whole connect sweep as one write (how the official app does it)",
    )
    args = p.parse_args()

    print(f"Opening {args.port} at {args.baud} 8N1 …")
    try:
        ser = open_serial(args.port, args.baud, timeout=0.1)
    except Exception as e:
        print(f"open failed: {e}")
        print("If this is Bluetooth, pair it in Windows Settings first so a COM port appears.")
        return 1

    with ser:
        print(f"open  name={ser.name!r}  in_waiting={ser.in_waiting}")
        leftover = ser.read(1024)
        if leftover:
            print("bytes already in buffer (maybe a banner):")
            print(hexdump(leftover, "  "))

        if args.one_shot:
            tx = sweep_bytes()
            print(f"\n>> sweep ({len(tx)} bytes)\n{hexdump(tx, '  ')}")
            rx = transact(ser, tx, args.wait * 3)
            print(f"\n<< {len(rx)} bytes\n{hexdump(rx, '  ')}")
            _report(rx)
            return 0 if rx else 2

        any_rx = False
        for name in CONNECT_SWEEP:
            tx = get_cmd(name)
            print(f"\n>> {name}  {tx.hex()}")
            rx = transact(ser, tx, args.wait)
            if not rx:
                print("<< (timeout)")
                continue
            any_rx = True
            print(f"<< {len(rx)} bytes")
            print(hexdump(rx, "  "))
            _report(rx)

        if not any_rx:
            print(
                "\nNo replies. Try --baud 9600, confirm the COM port with identify.py, "
                "or capture Print Master (see docs/reverse-engineering.md)."
            )
            return 2
    return 0


def _report(rx: bytes) -> None:
    guess = family_guess(rx)
    if guess:
        print(f"  family: {guess}")
    replies = parse_replies(rx)
    if not replies and rx:
        print("  (no 1A-tagged replies parsed — dump the hex into the capture notes)")
        return
    for tag, payload, desc in replies:
        print(f"  1A {tag:02x}  {desc}  raw={payload.hex()}")


if __name__ == "__main__":
    raise SystemExit(main())
