# Ponek M100 — open interface

Drive a Ponek M100 portable label printer without Print Master / Labelife.

The wire protocol on this unit is confirmed. `src/m100` is a Python client and a browser designer that print 40×30 mm gap labels over Bluetooth (SPP on Windows, BLE on Android Chrome).

The M100 is a white-label **Aimotech / Quyin** handheld (Print Master + Labelife), same family as Phomemo M110-class roll printers.

| Clue | What it points to |
|---|---|
| Official mobile app is **Print Master** | Aimotech (`com.project.aimotech.printmaster`) |
| Official PC app is **Labelife** over USB | Same OEM family as Phomemo / Aimo / Munbyn |
| Print Master UI has an explicit **M100** model | `M100Printer` exists in the Aimotech SDK |
| Hardware: 203 DPI, 20–50 mm rolls, Type-C | Aimotech M-series |
| Amazon model `CY-M100-BK-1` / `CY-M100-WH-1` | Typical Aimotech rebrand SKU |

Protocol references:

- `refs/web-based-label-studio/protocol.md` — Aimotech `1F 11` / `1A` command set
- `refs/phomemo-tools` — Phomemo M110/M120/M220 raster encoding

Full notes: [`docs/findings.md`](docs/findings.md), [`field-notes.md`](field-notes.md).

## Print from Python

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m m100 COM10 status
python -m m100 COM10 test
python -m m100 COM10 print .\some-label.png
python -m m100 serve
```

`python -m m100 serve` opens the designer at http://127.0.0.1:8765/.

**Phone (Android Chrome):** Web Bluetooth needs HTTPS, so on the PC:

```powershell
python -m m100 serve --lan
```

Open the printed `https://<pc-ip>:8765/` on the phone, accept the cert warning, tap **Connect Bluetooth**, pick **M100**. iPhone Safari cannot do Web Bluetooth.

**Windows PC:** this printer is bonded as COM10, so Connect Bluetooth opens the serial picker. That is still Bluetooth, just Classic SPP.

```python
from m100 import M100Client

with M100Client("COM10") as printer:
    print(printer.status())
    printer.print_file("label.png")
```

Dark pixels burn. Images are fitted into 40×30 mm at 203 DPI and shifted 3.5 mm right onto the 384 px head. Details: [`src/README.md`](src/README.md).

## Hardware

| | |
|---|---|
| Brand / model | Ponek M100 (`CY-M100-*`) |
| Print | Direct thermal, 203 DPI, ~20 mm/s |
| Media | 20–50 mm (0.78–2") die-cut or continuous. Stock roll is 40×30 mm |
| Links | Bluetooth (phone) + USB Type-C (PC) |
| Apps | Print Master (iOS/Android), Labelife (Windows/Mac USB) |

## Install as a server (Debian)

The designer is a small HTTPS app. Phones talk to the **printer over Bluetooth**; the Debian host only serves the web UI. It does not need a Bluetooth adapter unless you also want to print from the server itself.

### Packages and app user

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

sudo useradd --system --home /opt/m100 --shell /usr/sbin/nologin m100
sudo mkdir -p /opt/m100
sudo chown m100:m100 /opt/m100
```

Copy this repo onto the box (git clone, rsync, or scp), then:

```bash
sudo -u m100 git clone <your-repo-url> /opt/m100
# or: sudo rsync -a ./ /opt/m100/ && sudo chown -R m100:m100 /opt/m100

cd /opt/m100
sudo -u m100 python3 -m venv /opt/m100/.venv
sudo -u m100 /opt/m100/.venv/bin/pip install -U pip
sudo -u m100 /opt/m100/.venv/bin/pip install -e /opt/m100
```

### Firewall

```bash
sudo apt install -y ufw
sudo ufw allow 8765/tcp comment "M100 designer"
sudo ufw reload
```

If you use nftables/firewalld instead, allow TCP **8765** inbound on the LAN interface.

### systemd

A unit file lives at [`deploy/m100.service`](deploy/m100.service):

```bash
sudo cp /opt/m100/deploy/m100.service /etc/systemd/system/m100.service
sudo systemctl daemon-reload
sudo systemctl enable --now m100
sudo systemctl status m100
```

First start writes a self-signed cert to `/opt/m100/.certs/`. Check the listening address:

```bash
sudo journalctl -u m100 -e
# look for:  phone    https://<lan-ip>:8765/
```

On a phone (Android Chrome, same LAN): open that URL, accept the certificate warning, tap **Connect Bluetooth**, pick **M100**.

Useful commands:

```bash
sudo systemctl restart m100
sudo systemctl stop m100
sudo journalctl -u m100 -f
```

`--lan` binds `0.0.0.0` and enables HTTPS (Web Bluetooth requires a secure origin). `--no-browser` is required on a headless host.

### Optional: print from the Linux box

Pair the printer with BlueZ, then use the Python client against the RFCOMM device:

```bash
sudo apt install -y bluez
bluetoothctl
# power on
# scan on
# pair <M100 MAC>
# trust <M100 MAC>
# quit
sudo rfcomm bind 0 <M100 MAC>
sudo -u m100 /opt/m100/.venv/bin/python -m m100 /dev/rfcomm0 status
```

Add the `m100` user to the `dialout` (and maybe `bluetooth`) groups if permission is denied.

## Probe tools

```powershell
python tools\identify.py
python tools\probe_serial.py COM10
python tools\probe_ble.py --name M100
```

Capture playbook: [`docs/reverse-engineering.md`](docs/reverse-engineering.md). Wire format: [`docs/protocol-hypothesis.md`](docs/protocol-hypothesis.md).

## Repo layout

```
docs/                         research + capture playbook
tools/                        Windows identify / probe / test-print
captures/                     drop btsnoop / pcapng here (gitignored)
src/m100                      Python client + browser designer
refs/phomemo-tools            M110 raster encoder
refs/web-based-label-studio   Aimotech Print Master protocol notes
```

## Legal

This is an interoperability project for a printer you own. We document observable bytes and reimplement them. We do not ship Print Master, Labelife, firmware images, or decompiled APKs.
