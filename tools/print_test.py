"""Send a Phomemo-M110-style test raster over a serial port.

Only run this after probe_serial.py (or probe_ble.py) has gotten a
1A-tagged reply. The encoder is the published M110 sequence — if this
unit wants SET_PRINT_IMAGE instead, the print will be garbage or
nothing, which is still a useful negative result.

A high-contrast 'TEST' block makes inversion / width-padding obvious.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aimotech import hexdump  # noqa: E402

DPI = 203.0


def mm_to_px(mm: float, min_px: int = 0) -> int:
    return max(min_px, int(round(mm / 25.4 * DPI)))


def render_test(width_px: int, height_px: int, inset_px: int):
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    im = Image.new("L", (width_px, height_px), 255)
    d = ImageDraw.Draw(im)
    x0, y0 = inset_px, inset_px
    x1, y1 = width_px - 1 - inset_px, height_px - 1 - inset_px
    d.rectangle([x0, y0, x1, y1], outline=0, width=3)
    sq = min(32, (x1 - x0) // 4)
    d.rectangle([x0 + 8, y0 + 8, x0 + 8 + sq, y0 + 8 + sq], fill=0)
    try:
        font = ImageFont.truetype("arial.ttf", size=max(22, (y1 - y0) // 4))
    except OSError:
        font = ImageFont.load_default()
    d.text((x0 + (x1 - x0) // 6, y0 + (y1 - y0) // 3), "TEST", fill=0, font=font)
    # thermal: bit 1 = burn. invert then mode '1' makes drawings print black.
    return ImageOps.invert(im).convert("1")


def m110_job(image, speed: int, density: int, media: int) -> bytes:
    """Init + M110 header + GS v 0 raster + M110 footer only.

    Do not AUTO_LOCATE after a full (or nearly full) label — that seeks
    the *next* gap and feeds most of the following sticker. Do not ESC d
    extra feed either; GS v 0 already advanced the paper by image.height.
    """
    buf = bytearray()
    buf += b"\x1b\x40"
    buf += b"\x1b\x4e\x0d" + bytes([speed])
    buf += b"\x1b\x4e\x04" + bytes([density])
    buf += b"\x1f\x11" + bytes([media])
    width_bytes = (image.width + 7) // 8
    buf += b"\x1d\x76\x30\x00"
    buf += width_bytes.to_bytes(2, "little")
    buf += image.height.to_bytes(2, "little")
    buf += image.tobytes()
    buf += b"\x1f\xf0\x05\x00"
    buf += b"\x1f\xf0\x03\x00"
    return bytes(buf)


def write_paced(ser, payload: bytes, chunk: int, delay: float) -> None:
    sent = 0
    while sent < len(payload):
        n = ser.write(payload[sent : sent + chunk])
        ser.flush()
        sent += n
        if sent < len(payload) and delay:
            time.sleep(delay)
        if sent % (chunk * 8) < chunk or sent == len(payload):
            print(f"  sent {sent}/{len(payload)}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("port")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--width-mm", type=float, default=40.0, help="label width")
    p.add_argument("--height-mm", type=float, default=30.0, help="label height (used to compute printable rows)")
    p.add_argument("--head-px", type=int, default=384, help="print-head width in pixels")
    p.add_argument("--shift-right-mm", type=float, default=3.5, help="nudge artwork toward the right of the head")
    p.add_argument("--pad-top-mm", type=float, default=0.0, help="blank rows at the start of the raster (feed direction)")
    p.add_argument("--bottom-margin-mm", type=float, default=0.0, help="leave this much of the label unprinted")
    p.add_argument("--inset-mm", type=float, default=2.0, help="frame inset inside the artwork box")
    p.add_argument("--speed", type=int, default=3)
    p.add_argument("--density", type=int, default=10)
    p.add_argument("--media", type=int, default=0x0A, help="0A=gap 0B=continuous 26=black-mark")
    p.add_argument("--chunk", type=int, default=256, help="Bluetooth SPP write size")
    p.add_argument("--pace-ms", type=float, default=20.0, help="delay between chunks")
    p.add_argument("--hold", type=float, default=12.0, help="seconds to keep COM port open after send")
    p.add_argument("--dry-run", action="store_true", help="write captures/last-job.bin, do not open the port")
    p.add_argument("--i-know-what-im-doing", action="store_true")
    args = p.parse_args()

    if not args.dry_run and not args.i_know_what_im_doing:
        print(
            "Refusing to print until you have a successful probe.\n"
            "Re-run with --i-know-what-im-doing after probe_serial.py answers,\n"
            "or --dry-run to inspect the bytes."
        )
        return 2

    content_w = mm_to_px(args.width_mm, min_px=8)
    printable_h_mm = max(8.0, args.height_mm - args.pad_top_mm - args.bottom_margin_mm)
    content_h = mm_to_px(printable_h_mm, min_px=8)
    pad_top = mm_to_px(args.pad_top_mm)
    shift_x = mm_to_px(args.shift_right_mm)
    inset = mm_to_px(args.inset_mm)
    head = max(args.head_px, content_w + shift_x)
    page_h = pad_top + content_h
    from PIL import Image

    inner = render_test(content_w, content_h, inset)
    page = Image.new("1", (head, page_h), 0)
    page.paste(inner, (shift_x, pad_top))

    job = m110_job(page, args.speed, args.density, args.media)
    out = Path(__file__).resolve().parents[1] / "captures" / "last-job.bin"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(job)
    print(
        f"job {len(job)} bytes  page {head}x{page_h} px  "
        f"art {content_w}x{content_h} at +{shift_x}x+{pad_top}  wrote {out}"
    )
    print(hexdump(job[:64], "  "))
    print("  …")

    if args.dry_run:
        return 0

    try:
        import serial
    except ImportError as e:
        raise SystemExit("pip install pyserial pillow") from e

    print(f"writing to {args.port} in {args.chunk}B chunks, {args.pace_ms}ms pace, hold {args.hold}s …")
    with serial.Serial(args.port, baudrate=args.baud, timeout=1, write_timeout=10) as ser:
        write_paced(ser, job, args.chunk, args.pace_ms / 1000.0)
        deadline = time.time() + args.hold
        drained = bytearray()
        print(f"holding link {args.hold:.0f}s so the printer can finish…")
        while time.time() < deadline:
            chunk = ser.read(256)
            if chunk:
                drained.extend(chunk)
            else:
                time.sleep(0.2)
        if drained:
            print("reply:")
            print(hexdump(bytes(drained), "  "))
        else:
            print("no reply while holding (can still be a good print)")
    print("done — should be one 40x30 mm label, no extra feed into the next one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
