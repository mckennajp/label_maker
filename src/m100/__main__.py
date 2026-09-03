"""CLI: python -m m100 COM10 status | test | print image.png"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python src/m100/...` and `python -m m100` from the repo root.
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from m100.client import M100Client  # noqa: E402
from m100.protocol import PrinterStatus  # noqa: E402


def _show(st: PrinterStatus) -> None:
    print(f"  serial    {st.serial}")
    print(f"  firmware  {st.firmware}")
    print(f"  battery   {st.battery_percent}%")
    print(f"  paper     {st.paper}")
    print(f"  cover     {st.cover}")
    print(f"  temp      {st.hot}")
    print(f"  media     {st.label_type}")
    if st.print_complete:
        print("  print     complete")


def _test_image():
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    from m100.raster import Geometry, mm_to_px

    geo = Geometry()
    w, h = geo.label_w_px, geo.label_h_px
    inset = mm_to_px(2.0)
    im = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(im)
    d.rectangle([inset, inset, w - 1 - inset, h - 1 - inset], outline=0, width=3)
    d.rectangle([inset + 8, inset + 8, inset + 40, inset + 40], fill=0)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    d.text((w // 5, h // 3), "TEST", fill=0, font=font)
    return ImageOps.invert(im).convert("1")


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m m100")
    p.add_argument("port", help="COM port (COM10) or 'serve' for browser Bluetooth")
    p.add_argument("command", nargs="?", default=None, help="status | test | print | serve")
    p.add_argument("image", nargs="?", help="image path for the print command")
    p.add_argument("--copies", type=int, default=1)
    p.add_argument("--width-mm", type=float)
    p.add_argument("--height-mm", type=float)
    p.add_argument("--http", type=int, default=8765, help="designer HTTP port (serve)")
    p.add_argument("--host", default=None, help="bind address (default 127.0.0.1; 0.0.0.0 for phones)")
    p.add_argument("--https", action="store_true", help="TLS (required for Web Bluetooth on a phone)")
    p.add_argument("--lan", action="store_true", help="phone mode: bind 0.0.0.0 + HTTPS")
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()

    if args.port == "serve" or args.command == "serve":
        from m100.server import serve

        com = None if args.port == "serve" else args.port
        host = args.host or ("0.0.0.0" if args.lan else "127.0.0.1")
        https = args.https or args.lan
        serve(com, http_port=args.http, open_browser=not args.no_browser, host=host, https=https)
        return 0
    if not args.command:
        p.error("command required: status | test | print | serve")

    with M100Client(args.port) as printer:
        if args.command == "status":
            _show(printer.status())
            return 0
        if args.command == "test":
            st = printer.print_image(_test_image(), copies=args.copies)
            _show(st)
            return 0 if st.print_complete else 2
        if not args.image:
            p.error("print requires an image path")
        st = printer.print_file(
            args.image,
            copies=args.copies,
            width_mm=args.width_mm,
            height_mm=args.height_mm,
        )
        _show(st)
        return 0 if st.print_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
