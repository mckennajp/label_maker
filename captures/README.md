# Captures

Drop packet dumps here. Do not commit them — `.gitignore` excludes the payloads.

Recommended filenames:

| File | What it is |
|---|---|
| `01-connect.btsnoop` | Print Master connect + status sweep, no print |
| `02-print-one-label.btsnoop` | Single 40×30 mm label, known content (e.g. the letter `A`) |
| `03-print-two-copies.btsnoop` | Same label, 2 copies |
| `04-usb-print.pcapng` | Labelife USB print of the same label |
| `identify.txt` | Output of `python tools/identify.py` |

See `docs/reverse-engineering.md` for how to produce each dump.
