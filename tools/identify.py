"""Inventory what the Ponek M100 looks like on this PC.

Prints:
  - BLE advertisements (name, address, RSSI, service UUIDs)
  - Serial / COM ports
  - On Windows, PnP Bluetooth and USB devices that look printer-related

Does not connect or send printer commands.
"""

from __future__ import annotations

import argparse
import asyncio
import platform
import re
import subprocess
import sys

KNOWN_BLE = {
    "0000ff00-0000-1000-8000-00805f9b34fb": "Aimotech/Quin FF00 (write ff02 / notify ff01)",
    "e7810a71-73ae-499d-8c15-faa9aef0c3f2": "NIIMBOT (unexpected for a Ponek M100)",
    "0000ae30-0000-1000-8000-00805f9b34fb": "Cat-printer AE30",
    "000018f0-0000-1000-8000-00805f9b34fb": "MTP / ESC-POS 18F0",
    "49535343-fe7d-4ae5-8fa9-9fafd205e455": "ISS C / alternate Quin",
}

NAME_HINT = re.compile(
    r"m100|m110|m120|m220|ponek|aimo|phomemo|print|label|cy-m",
    re.I,
)


def _short_uuid(u: str) -> str:
    u = str(u).lower()
    return KNOWN_BLE.get(u, u)


async def scan_ble(seconds: float) -> None:
    try:
        from bleak import BleakScanner
    except ImportError:
        print("BLE: install bleak  (pip install -r tools/requirements.txt)")
        return

    print(f"\n=== BLE scan ({seconds:.0f}s) ===")
    print("Power the printer on and keep it next to the PC.\n")
    devices = await BleakScanner.discover(timeout=seconds, return_adv=True)
    if not devices:
        print("  (no BLE advertisements seen)")
        return

    hits = []
    others = []
    for addr, (dev, adv) in devices.items():
        name = dev.name or adv.local_name or ""
        uuids = [str(x).lower() for x in (adv.service_uuids or [])]
        row = (name, addr, adv.rssi, uuids)
        if NAME_HINT.search(name) or any(u in KNOWN_BLE for u in uuids):
            hits.append(row)
        else:
            others.append(row)

    def dump(title: str, rows: list) -> None:
        print(title)
        if not rows:
            print("  (none)")
            return
        rows.sort(key=lambda r: r[2] if r[2] is not None else -999, reverse=True)
        for name, addr, rssi, uuids in rows:
            label = name or "(no name)"
            print(f"  {label:24s}  {addr}  RSSI {rssi}")
            for u in uuids:
                print(f"      service  {_short_uuid(u)}")
            if not uuids:
                print("      (no service UUIDs in advertisement — connect to enumerate)")

    dump("Likely printer / known thermal-printer UUIDs:", hits)
    print()
    dump("Other BLE devices (for context):", others)


def list_serial_ports() -> None:
    try:
        from serial.tools import list_ports
    except ImportError:
        print("\nSerial: install pyserial  (pip install -r tools/requirements.txt)")
        return

    print("\n=== Serial / COM ports ===")
    print("Unplug USB, run this, plug USB, run again — the new COM port is the printer.\n")
    ports = list(list_ports.comports())
    if not ports:
        print("  (no serial ports)")
        return
    for p in ports:
        hwid = p.hwid or ""
        vidpid = ""
        m = re.search(r"VID:PID=([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})", hwid)
        if m:
            vidpid = f"  USB {m.group(1)}:{m.group(2)}"
        hint = ""
        blob = f"{p.device} {p.description} {p.manufacturer} {hwid}"
        if NAME_HINT.search(blob) or "Bluetooth" in hwid or "BTHENUM" in hwid:
            hint = "  <-- look here"
        print(f"  {p.device:8s}  {p.description}{vidpid}{hint}")
        if p.manufacturer:
            print(f"            manufacturer={p.manufacturer}")
        if hwid:
            print(f"            {hwid}")


def _pnp(filter_script: str, title: str) -> None:
    if platform.system() != "Windows":
        return
    print(f"\n=== {title} ===\n")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", filter_script],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"  (powershell failed: {e})")
        return
    out = (r.stdout or "").strip()
    if not out:
        print("  (none)")
        return
    print(out)


def windows_pnp() -> None:
    if platform.system() != "Windows":
        return
    _pnp(
        r"""
Get-PnpDevice -PresentOnly |
  Where-Object {
    $_.FriendlyName -match 'Bluetooth|Serial|COM|Printer|M100|Label|Print|USB Serial|Virtual COM' -or
    $_.InstanceId -match 'BTHENUM|USB\\VID'
  } |
  Select-Object Status, Class, FriendlyName, InstanceId |
  Format-Table -AutoSize | Out-String -Width 220
""",
        "Windows PnP (Bluetooth / serial / USB, present)",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ble-seconds", type=float, default=8.0)
    parser.add_argument("--no-ble", action="store_true")
    args = parser.parse_args()

    print(f"OS: {platform.system()} {platform.release()}  Python {sys.version.split()[0]}")
    print("Tip: run once with the printer off, once with it on, once with USB plugged in.")

    if not args.no_ble:
        asyncio.run(scan_ble(args.ble_seconds))
    list_serial_ports()
    windows_pnp()

    print(
        "\nNext:\n"
        "  python tools/probe_serial.py COMx     # USB or paired Bluetooth SPP\n"
        "  python tools/probe_ble.py --name M100 # if BLE scan found it\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
