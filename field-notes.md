# Field notes — Ponek M100 (this unit)

Confirmed 2026-09-02 on Windows 11 after pairing.

## Identify

- BLE advertised name: `M100`
- BLE address: `DB:3E:21:4B:6E:05`
- Advertised service UUIDs: `0000af30-…`, HID `00001812-…`
- After GATT connect: print service is `0000ff00-…` (FF02 write, FF03 notify)
- USB: not tried yet
- Bluetooth paired in Windows → **COM10** (SPP UUID `00001101-…`, address `DB3E214B6E05`)
- Also paired as BLE device `BTHENUM\DEV_DB3E214B6E05`
- BLE notify/write from Python still hits “Insufficient Authentication”; SPP works without that

## Probe (`python tools/probe_serial.py COM10`)

Aimotech/Quin `1F 11` / `1A` replies.

| Query | Reply |
|---|---|
| serial `1F 11 09` | `Q378E6640690061` (SN prefix **Q378**) |
| firmware `1F 11 07` | **0.1.1** (`00 01 01`) |
| battery `1F 11 08` | 100% (`0x64`) |
| paper `1F 11 11` | ok (`0x89`) |
| cover `1F 11 12` | closed (`0x98`) |
| hot `1F 11 13` | ok (`0xA8`) |
| label type `1F 11 19` | **gap** (`0x0A`) |
| BT MAC `1F 11 20` | `DB3E214B6E05` |
| chip/BT ver `1F 11 38` | tag `1A 17` payload `03` (Jerry/JieLi family) |

## Working print path (40×30 mm gap labels)

Confirmed on this unit. Encoder is Phomemo M110 / Aimotech `GS v 0`.

| Setting | Value |
|---|---|
| Port | COM10 (Bluetooth SPP) |
| Head | 384 px (48 mm at 203 DPI) |
| Label | 40×30 mm → 320×240 px |
| Shift right | **3.5 mm** (28 px) |
| Pad top | **0 mm** |
| Frame inset | 2 mm (visual margin only) |
| Speed | 3 (`1B 4E 0D 03`) |
| Density | 10 (`1B 4E 04 0A`) |
| Media | gap `1F 11 0A` |
| Raster | `1D 76 30 00` + width/height LE + 1 bpp rows |
| Footer | `1F F0 05 00` / `1F F0 03 00` only — **no** `ESC d`, **no** auto-locate |
| Transport | 256-byte chunks, 20 ms pace, hold COM port ~12 s |
| Done | printer replies `1A 0F 0C` |

Do not auto-locate after a full-height raster — that feeds most of the next sticker.

BLE GATT (`FF00` / `FF02` / `FF03`) exists but Windows still wants extra auth; SPP is the working path.
