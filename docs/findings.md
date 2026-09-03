# Findings — Ponek M100

Status: **research complete, hardware not yet probed in this repo.**

## 1. What the M100 actually is

Ponek is a retail brand. The M100 is a 50 mm-class handheld thermal label printer from the **Aimotech / Zhuhai Quin / Quyin** OEM line, sold under many names (Aimo, Phomemo-adjacent SKUs, Erufale, Omezizy, …).

It is an Aimotech-family printer, not a cassette/RFID label maker.

### Official software (from the Ponek manual and Amazon listing)

| Role | Name | Transport |
|---|---|---|
| Phone | **Print Master** (App Store / Play) | Bluetooth |
| PC | **Labelife** from `labelife.net` / `M100.labelife.cc` | USB Type-C |

Print Master is Aimotech’s app. Package on Android: `com.project.aimotech.printmaster`. The in-app model picker has a dedicated **M100** entry, separate from the M110/M120/M200/M220 series.

The same SDK’s printer-class catalog (documented in `refs/web-based-label-studio/protocol.md` §15) includes:

```
M100, M102, M105, M108, M110, M110C, M120, M200, M220, M221, …
```

So there is a first-party `M100Printer` implementation. We just do not have its parameter table in an open driver yet.

### Physical spec (aggregated from the listing / manuals)

| | |
|---|---|
| Resolution | 203 DPI |
| Media width | 20–50 mm (included roll: 40×30 mm, 100 pcs) |
| Speed | ~15–30 mm/s |
| Battery | ~1200 mAh, auto-off ~15 min |
| I/O | Bluetooth + USB Type-C |
| Weight | ~282 g |
| Amazon model | `CY-M100-BK-1` / `CY-M100-WH-1` |

No RFID cassette is mentioned.

## 2. Protocol families in this hardware class

Cheap 50 mm Bluetooth label printers almost always fall into one of three buckets:

| Family | Apps | Wire | Open work |
|---|---|---|---|
| **Aimotech / Quin** | Print Master, Labelife, Phomemo | ESC/POS + vendor `1F 11 xx` | web-based-label-studio, phomemo-tools, thermal-label/labelife |
| **Marklife / “cat printer”** | various | `51 78` framed BLE | print_master_ble, LaBLEr |

The M100’s apps put it in bucket 2.

Inside that bucket there are still two raster dialects:

1. **P780BT / tape printers** — identify with `1F 11 09` (serial), print with `1B 4E 1F` + packed 1-bpp rows, end with `1B 64 xx`. Documented end-to-end in `refs/web-based-label-studio/protocol.md`.
2. **M110 / M120 / M220 roll printers** — same `1F 11` status commands, print with ESC/POS `GS v 0` (`1D 76 30`) raster, header `1B 4E 0D` speed + `1B 4E 04` density + `1F 11 0A` gap paper, footer `1F F0 05 00` / `1F F0 03 00`. Implemented in `refs/phomemo-tools/cups/filter/rastertopm110.py`.

The M100 is a **roll** printer with a 50 mm head, so dialect 2 is the prior. Confirm on the wire before writing a driver — Aimotech has used both on M-series units, and the `*C` M-models add an LZO/NV compression layer we do not want to guess at.

## 3. Transport: BLE vs Classic SPP vs USB

Aimotech handhelds are often **dual-mode** (JieLi AC69xx “Jerry” chip): Classic SPP for the phone app, USB CDC ACM (“USB Virtual COM”, often Nuvoton) for Labelife.

Print Master on Android may use:

- Classic RFCOMM / SPP (service name `JL_SPP` on JieLi chips, UUID `00001101-0000-1000-8000-00805F9B34FB`), or
- BLE GATT (`0000ff00-…` / write `ff02` / notify `ff01`) on some M-series firmware.

We will not know which this Ponek unit uses until `tools/identify.py` runs against it. On Windows:

- USB Type-C almost always shows up as a **COM port**.
- Classic SPP, once paired in Windows Bluetooth settings, also shows up as a **COM port**.
- BLE does **not** become a COM port; use Web Bluetooth or Python `bleak`.

## 4. Existing code we can steal from (not copy APKs)

| Project | Use for |
|---|---|
| `refs/phomemo-tools/cups/filter/rastertopm110.py` | First print encoder to try (speed/density/media + `GS v 0`) |
| `refs/web-based-label-studio/protocol.md` | Full `1F 11` GET/SET table, response tags, SN-prefix idea |
| `refs/web-based-label-studio/{base,models,transport}.js` | Web Serial driver shape if we keep a browser UI |
| [thermal-label/labelife](https://github.com/thermal-label/labelife) | TypeScript catalog of ~95 Labelife models (no M100 row yet) |
| [vivier/phomemo-tools](https://github.com/vivier/phomemo-tools) | CUPS + Bluetooth backend if we ever want OS printing |

## 5. Open questions (need the printer)

Answer these with `tools/identify.py` and one Print Master capture:

1. Bluetooth advertised name (`M100`, `CY-M100`, MAC suffix, …)?
2. Classic SPP, BLE, or both?
3. BLE service / characteristic UUIDs, if BLE.
4. USB VID:PID and whether it is CDC ACM.
5. Serial number prefix (Aimotech SNs often start with `Q` + 3 digits).
6. Which raster command the official app uses (`1D 76 30` vs `1B 4E 1F` vs compressed).
7. Printable width in dots (384 vs 400 vs something else).
8. Whether gap-sensor commands (`1F 11 0B` / `1F 11 25`) are required before the first print.
