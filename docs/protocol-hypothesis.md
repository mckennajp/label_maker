# Protocol hypothesis — Ponek M100

Nothing in this file is confirmed on a Ponek unit. It is the union of:

- Aimotech Print Master SDK command table (`refs/web-based-label-studio/protocol.md`)
- Phomemo M110/M120/M220 USB dump (`refs/phomemo-tools` §5 and `rastertopm110.py`)

Use it as a decoder ring for captures and as the command list `tools/probe_serial.py` sends.

## Transport

| Pipe | Likely shape |
|---|---|
| USB Type-C | CDC ACM serial, 115200 8N1 (sometimes 9600; probe tries 115200 first) |
| Classic BT | SPP / RFCOMM channel 1, UUID `00001101-0000-1000-8000-00805F9B34FB` |
| BLE | Service `0000ff00-0000-1000-8000-00805f9b34fb`, write `ff02`, notify `ff01`, optional flow `ff03` |

No extra framing on SPP/USB — commands are raw bytes concatenated in one stream.

Unexpected framing (`55 55 …` or `51 78`) means this is not the Aimotech dialect; stop and re-identify the family.

## Status: host → printer

Prefix `1F 11 <cmd>`. Several may be concatenated.

| cmd | Name | Expected reply tag |
|---:|---|---|
| `0x38` | CHIP_TYPE | `1A 3B` (3 flag bytes) |
| `0x11` | PAPER_STATE | `1A 06` — `88` empty, `89` ok |
| `0x12` | COVER_STATE | `1A 05` — `98` closed, `99` open |
| `0x13` | HOT_STATE | `1A 03` — `A8` ok, `A9` hot |
| `0x09` | SERIAL | `1A 08` + 15 ASCII |
| `0x07` | FIRMWARE | `1A 07` + 3 bytes `major.minor.patch` |
| `0x08` | BATTERY | `1A 04` + 1 byte (`00` often means full) |
| `0x19` | LABEL_TYPE | `1A 0C` — `0A` gap, `0B` continuous, `26` black mark |
| `0x20` | BT_MAC | 12 ASCII hex |

## Status: printer → host

Prefix `1A <tag> <payload>`. Asynchronous (cover open mid-print) is allowed.

## Print path A — Phomemo M110 (first guess)

Used by M110/M120/M220 roll printers. Implemented in `refs/phomemo-tools/cups/filter/rastertopm110.py`.

```
1B 4E 0D  05          speed     1 = slow … 5 = fast
1B 4E 04  0A          density   1 … 0F
1F 11     0A          media     0A gap, 0B continuous, 26 black mark

1D 76 30  00  W_LO W_HI  H_LO H_HI
              mode=0 (normal)
              W = bytes per line = ceil(width_px / 8)
              H = number of rows in this block
< W * H bytes, 1 bpp, MSB leftmost, 1 = black >

1F F0 05 00
1F F0 03 00
```

M110 capture used `W = 0x2B` (43 bytes = 344 px) and `H = 0x00F0` (240 rows). A 40×30 mm label on a 50 mm head will likely be **padded to head width**, not packed to 40 mm.

## Print path B — Aimotech `SET_PRINT_IMAGE`

Used by P780BT and other tape units:

```
1B 40                          ESC @ init
1B 4E 1F  <nv raster>          SET_PRINT_IMAGE
1F 11 3C                       pause between copies (optional)
1B 64 00                       print-and-feed (end-of-job; length is model-specific)
```

NV raster shape (from the SDK’s `img2Nv`):

```
30 00  W_LO W_HI  <rows...>
```

If a capture starts with `1B 4E 1F` or `1B 40` instead of `1B 4E 0D`, switch the encoder to this path.

## Print path C — compressed (avoid until proven)

`M110C` / `M120C` / `M200C` / `M220C` add `img2NvCompress` / minilzo. CHIP_TYPE flags:

- `d0 & 0x08` compress
- `d0 & 0x10` minilzo
- `d0 & 0x20` huffman

Enter/exit: `1F 11 35 01` / `1F 11 35 00`. If the official app sends `35 01` before the bitmap, we need a capture of the compressed payload — do not invent it.

## Geometry to assume until measured

| | Value | Why |
|---|---|---|
| DPI | 203 | listing |
| Max paper | 50 mm | listing |
| Head width | 384 px (48 mm) or 400 px (50 mm) | common for this class; M110 used 344 px |
| Default label | 40×30 mm → ~320×240 px of *content* | included roll |
| Gap stock | media byte `0x0A` | die-cut 40×30 |

## Flow control

BLE writes may need credit-based pacing on `ff03` (`01 <credits>`). USB/SPP usually does not. If prints start then stall, the capture’s inter-packet timing matters — Aimotech apps often wait for `PRINT_BUSY` (`1F 11 54` / tag `1A 62`) to go idle.

## What a positive identification looks like

```
>> 1f 11 09
<< 1a 08 51 32 …                 SN, ASCII, often Qxxx...
>> 1f 11 07
<< 1a 07 00 01 09                e.g. firmware 0.1.9
>> 1f 11 11
<< 1a 06 89                      paper ok
```

If instead you see `55 55 … aa aa` packets or `51 78` cat-printer frames, stop and we switch families.
