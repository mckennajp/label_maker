# Reverse-engineering playbook

Goal: capture one successful official print, then replay the bytes from our own code.

Work in this order. Stop when you have a COM port that answers `1F 11 09` (serial number) — that is enough to start probing without the vendor app.

## 0. Ground rules

- One action per capture file. “Connect then print then change density” in the same dump is painful to attribute.
- Use a **known** test label: 40×30 mm, a large letter `A` in black, one copy. Same label for Bluetooth and USB.
- Do not flash firmware. Identification and print-path bytes are enough.
- Keep captures in `captures/` (gitignored).

## 1. Inventory the device (Windows, no vendor app)

Printer on, sitting next to the PC.

```powershell
python tools\identify.py
```

That script:

- BLE-scans for ~8 s and prints name, address, RSSI, advertised service UUIDs
- Lists serial ports (USB CDC and paired Bluetooth SPP both show up here)
- On Windows, also dumps PnP Bluetooth + USB devices whose names look printer-like

Write down:

- BLE name and whether service `0000ff00-…` or the NIIMBOT UUID appears
- Any new COM port that appears when you plug in USB, and again after pairing Bluetooth in Windows Settings
- USB VID:PID if Device Manager shows it

### Pairing Classic Bluetooth on Windows

Settings → Bluetooth → add device. If the printer shows up as a **headset-style** or **serial** device and Windows assigns a COM port, that is SPP. If it only appears to nRF Connect / `identify.py` as BLE and never gets a COM port, we talk GATT.

### USB

Plug the Type-C cable. Labelife talks this path. In Device Manager look for:

- “USB Serial Device (COMx)”
- “USB Virtual COM”
- A printer-class device (less likely)

`identify.py` should show the new COM port. That is the easiest probe target.

## 2. Active probe (no vendor app)

```powershell
python tools\probe_serial.py COM5
```

or, for BLE:

```powershell
python tools\probe_ble.py --name M100
```

These send the Aimotech identification sweep (`CHIP_TYPE`, `PAPER`, `COVER`, `HOT`, `SN`, `FW`) and print whatever comes back, hex + parsed tags.

Success looks like a `1A 08 …` serial-number reply (often 15 ASCII bytes starting with `Q`). Failure (timeout, empty) still tells us the transport is wrong or the command prefix is wrong — capture the official app next.

## 3. Capture Print Master (Android) — best source

This is the method that produced the Aimotech protocol doc.

1. Phone: Developer options → **Enable Bluetooth HCI snoop log**.
2. Toggle Bluetooth off/on so a fresh log starts.
3. Open Print Master, select **M100**, connect. Stop. Save this as capture A.
4. Start a new log (Bluetooth off/on again). Print **one** 40×30 mm label with a big `A`. Stop. Capture B.
5. Optional: two copies of the same label. Capture C.
6. Pull the log:

```powershell
adb bugreport captures\bugreport.zip
```

Inside the zip, look for `btsnoop_hci.log` (often under `FS/data/misc/bluetooth/logs/`). Copy it to `captures/`.

Open in Wireshark. Useful display filters once you know the printer MAC:

```
bluetooth.addr == aa:bb:cc:dd:ee:ff
btspp
btatt
btatt.opcode == 0x12 || btatt.opcode == 0x1b
```

- `btspp` traffic → Classic SPP, dialect is the Aimotech `1F 11` / `1D 76 30` world.
- `btatt` writes to a GATT characteristic → BLE. Note the UUID being written.

## 4. Capture Labelife (Windows USB)

USB is usually a byte-for-byte twin of the Bluetooth payload (same ESC/POS stream, different pipe). One USB dump lets us iterate without the phone.

1. Install [USBPcap](https://desowin.org/usbpcap/) + Wireshark.
2. Reboot if the installer asks.
3. `USBPcapCMD.exe` → pick the hub that lists the printer → filename `captures/04-usb-print.pcapng`.
4. Open Labelife, print the same `A` label, Ctrl+C the capture.

Wireshark: USB URB bulk out/in to that device. The payload should start with `1B 4E` or `1F 11` or `1D 76`.

Chrome/Edge **Web Serial** can also talk to the same COM port later; we do not need USBPcap once the bytes are known.

## 5. What to extract from a print capture

For the print job, list every host→printer payload in order. You want:

1. Init / status sweep (the `1F 11 xx` queries)
2. Speed, density, media-type (`1B 4E 0D`, `1B 4E 04`, `1F 11 0A` or similar)
3. Raster start (`1D 76 30` or `1B 4E 1F`) and the width/height fields
4. Raw 1-bpp rows
5. Footer / feed / gap-seek
6. Any ACK from the printer (`1A …`) that the app waits on

Also note:

- Bytes per line (printable width in pixels = that × 8)
- Number of lines (label length in pixels)
- Whether the bitmap is inverted (thermal: 1 = burn = black)
- Chunk size (BLE MTU vs USB bulk)

A 40×30 mm label at 203 DPI is roughly:

- width  40 / 25.4 × 203 ≈ **320 px** (40 bytes/line if packed)
- height 30 / 25.4 × 203 ≈ **240 px**

If the capture uses 43 bytes/line (344 px), that is the Phomemo M110 “full 50 mm head, unused columns padded” layout. If it uses 48 bytes/line (384 px), that is a 48 mm head.

## 6. Replay

Once the sequence is listed:

```powershell
python tools\print_test.py COM5 --width-mm 40 --height-mm 30
```

That script currently emits the **Phomemo M110** header/raster/footer. If the capture used a different raster command, we change four functions and try again. Keep the first test a high-contrast `TEST` block so a shifted/inverted print is obvious.

## 7. After a successful replay

Then, and only then, pick a UI:

| Want | Base |
|---|---|
| Fastest path to “print from PC” | Keep the Python driver, add a tiny CLI |
| Browser designer | `src/m100` designer, or fork `refs/web-based-label-studio` |

## 8. Windows capture extras

Wireshark 4.7+ can capture Bluetooth via `etwdump` (run as Administrator, add provider “Bluetooth Host Radio”). Useful if you run Print Master in an Android emulator or a phone’s Bluetooth is somehow bridged — usually Android HCI snoop is cleaner.

nRF Connect (phone) is enough to dump BLE GATT if `identify.py` sees a BLE device but `probe_ble.py` cannot write.
