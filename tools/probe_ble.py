"""Connect to a BLE printer, dump GATT, optionally send the Aimotech sweep.

Use this when identify.py sees a BLE advertisement and Windows did not
assign a COM port.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aimotech import (  # noqa: E402
    CONNECT_SWEEP,
    family_guess,
    get_cmd,
    hexdump,
    parse_replies,
)

FF00 = "0000ff00-0000-1000-8000-00805f9b34fb"
FF01 = "0000ff01-0000-1000-8000-00805f9b34fb"
FF02 = "0000ff02-0000-1000-8000-00805f9b34fb"
FF03 = "0000ff03-0000-1000-8000-00805f9b34fb"


WRITE_PROPS = {"write", "write-without-response"}


def _u(u) -> str:
    return str(u).lower()


async def find_device(name: str | None, address: str | None, timeout: float):
    from bleak import BleakScanner

    if address:
        dev = await BleakScanner.find_device_by_address(address, timeout=timeout)
        if not dev:
            raise SystemExit(f"no device at {address}")
        return dev

    print(f"Scanning {timeout:.0f}s for name containing {name!r} …")
    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    needle = (name or "m100").lower()
    matches = []
    for addr, (dev, adv) in found.items():
        label = (dev.name or adv.local_name or "").lower()
        if needle in label:
            matches.append(dev)
            print(f"  match {dev.name}  {addr}")
    if not matches:
        raise SystemExit("no name match — run identify.py and pass --address")
    if len(matches) > 1:
        print("multiple matches, using the first; pass --address to pick")
    return matches[0]


async def dump_gatt(client) -> tuple[str | None, str | None]:
    """Return (write_uuid, notify_uuid) guesses."""
    print("\n=== GATT ===")
    write_uuid = None
    notify_uuid = None
    for svc in client.services:
        print(f"service  {_u(svc.uuid)}  {svc.description}")
        for ch in svc.characteristics:
            props = set(ch.properties)
            print(f"  char   {_u(ch.uuid):36s}  [{','.join(sorted(props))}]  {ch.description}")
            cu = _u(ch.uuid)
            # Ponek M100: FF02 write, FF03 notify. Other Quin units use FF01 notify.
            if WRITE_PROPS & props:
                if cu == FF02 or write_uuid is None:
                    write_uuid = ch.uuid
            if "notify" in props:
                if cu in {FF03, FF01} or notify_uuid is None:
                    notify_uuid = ch.uuid
    return write_uuid, notify_uuid


async def run(args) -> int:
    try:
        from bleak import BleakClient
    except ImportError as e:
        raise SystemExit("pip install bleak") from e

    dev = await find_device(args.name, args.address, args.timeout)
    print(f"Connecting to {dev.name} {dev.address} …")
    async with BleakClient(dev, timeout=20) as client:
        print(f"connected  mtu={getattr(client, 'mtu_size', '?')}")
        write_uuid, notify_uuid = await dump_gatt(client)
        if args.dump_only:
            return 0
        if not write_uuid:
            print("no writable characteristic; cannot probe")
            return 2

        inbox: list[bytes] = []

        def on_notify(_handle, data: bytearray) -> None:
            inbox.append(bytes(data))
            print(f"<< notify {len(data)} bytes")
            print(hexdump(bytes(data), "  "))
            guess = family_guess(bytes(data))
            if guess:
                print(f"  family: {guess}")
            for tag, payload, desc in parse_replies(bytes(data)):
                print(f"  1A {tag:02x}  {desc}  raw={payload.hex()}")

        try:
            name_bytes = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
            print(f"GAP Device Name: {bytes(name_bytes)!r}")
        except Exception as e:
            print(f"GAP name read failed: {e}")
        try:
            ff01 = await client.read_gatt_char(FF01)
            print(f"FF01 read {len(ff01)} bytes")
            print(hexdump(bytes(ff01), "  "))
        except Exception as e:
            print(f"FF01 read failed: {e}")

        if notify_uuid:
            try:
                await client.start_notify(notify_uuid, on_notify)
                print(f"subscribed {notify_uuid}")
            except Exception as e:
                print(f"notify subscribe failed ({e}); trying pair() then retry")
                try:
                    await client.pair()
                    await client.start_notify(notify_uuid, on_notify)
                    print(f"subscribed {notify_uuid} after pair")
                except Exception as e2:
                    print(f"still no notify: {e2} — writes may still land")

        print(f"writing Aimotech sweep to {write_uuid}")
        for name in CONNECT_SWEEP:
            tx = get_cmd(name)
            print(f">> {name}  {tx.hex()}")
            await client.write_gatt_char(write_uuid, tx, response=False)
            await asyncio.sleep(args.wait)

        await asyncio.sleep(0.5)
        if not inbox:
            print(
                "No notifications. Pair the M100 in Windows Bluetooth settings "
                "(or plug USB and use probe_serial.py) so FF03 can notify."
            )
            return 2
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="M100", help="substring of BLE advertised name")
    p.add_argument("--address", help="BLE MAC / identifier from identify.py")
    p.add_argument("--timeout", type=float, default=8.0)
    p.add_argument("--wait", type=float, default=0.4)
    p.add_argument("--dump-only", action="store_true", help="enumerate GATT, send nothing")
    args = p.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
