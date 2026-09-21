"""M110-style 1-bpp raster and page layout for the Ponek M100."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageOps

DPI = 203.0
HEAD_PX = 384
SHIFT_RIGHT_MM = 4.8
PAD_TOP_MM = 0.0
DEFAULT_LABEL_MM = (40.0, 30.0)
DEFAULT_SPEED = 3
DEFAULT_DENSITY = 10
MEDIA_GAP = 0x0A


def mm_to_px(mm: float) -> int:
    return max(0, int(round(mm / 25.4 * DPI)))


@dataclass(frozen=True)
class Geometry:
    label_w_mm: float = DEFAULT_LABEL_MM[0]
    label_h_mm: float = DEFAULT_LABEL_MM[1]
    head_px: int = HEAD_PX
    shift_right_mm: float = SHIFT_RIGHT_MM
    pad_top_mm: float = PAD_TOP_MM

    @property
    def label_w_px(self) -> int:
        return mm_to_px(self.label_w_mm)

    @property
    def label_h_px(self) -> int:
        return mm_to_px(self.label_h_mm)

    @property
    def shift_x_px(self) -> int:
        return mm_to_px(self.shift_right_mm)

    @property
    def pad_top_px(self) -> int:
        return mm_to_px(self.pad_top_mm)

    @property
    def page_w_px(self) -> int:
        return self.head_px

    @property
    def page_h_px(self) -> int:
        return self.pad_top_px + self.label_h_px


_GAMMA_LUT = [int(round(255 * ((i / 255) ** (1 / 1.3)))) for i in range(256)]


def _thermal_gray(image: Image.Image) -> Image.Image:
    """BT.601 gray with gamma 1.3 — same lift Phomymo uses for thermal midtones."""
    if image.mode == "RGBA":
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[-1])
        image = bg
    gray = image.convert("L")
    return gray.point(_GAMMA_LUT)


def to_thermal_1bpp(image: Image.Image) -> Image.Image:
    """Mode '1' where bit 1 = burn = original dark pixels.

    Photos go through Floyd–Steinberg dithering so mid-grays survive as
    a halftone instead of a hard 50% threshold.
    """
    if image.mode == "1":
        return image
    gray = _thermal_gray(image)
    return ImageOps.invert(gray).convert("1", dither=Image.Dither.FLOYDSTEINBERG)


def fit_to_label(image: Image.Image, geo: Geometry) -> Image.Image:
    """Scale image to the 40×30 mm label box, then park it on the 384 px head.

    A 30×40 mm portrait bitmap is rotated 90° CW onto 40×30 stock.
    Taller stock such as 40×60 mm is printed as-is.
    """
    if image.height > image.width and geo.label_w_mm > geo.label_h_mm:
        image = image.transpose(Image.Transpose.ROTATE_270)
    box_w, box_h = geo.label_w_px, geo.label_h_px
    if image.mode == "1":
        gray = image.convert("L")
        gray.thumbnail((box_w, box_h), Image.Resampling.NEAREST)
        src = gray.convert("1", dither=Image.Dither.NONE)
    else:
        gray = _thermal_gray(image)
        gray.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
        src = ImageOps.invert(gray).convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    label = Image.new("1", (box_w, box_h), 0)
    ox = (box_w - src.width) // 2
    oy = (box_h - src.height) // 2
    label.paste(src, (ox, oy))
    page = Image.new("1", (geo.page_w_px, geo.page_h_px), 0)
    shift = geo.shift_x_px
    if shift + box_w > geo.head_px:
        shift = (geo.head_px - box_w) // 2
    page.paste(label, (shift, geo.pad_top_px))
    return page


def encode_job(
    page: Image.Image,
    speed: int = DEFAULT_SPEED,
    density: int = DEFAULT_DENSITY,
    media: int = MEDIA_GAP,
) -> bytes:
    """ESC @ + speed/density/gap + GS v 0 raster + M110 footer.

    No AUTO_LOCATE / ESC d — those over-feed the next die-cut label.
    """
    if page.mode != "1":
        page = to_thermal_1bpp(page)
    buf = bytearray()
    buf += b"\x1b\x40"
    buf += b"\x1b\x4e\x0d" + bytes([speed & 0xFF])
    buf += b"\x1b\x4e\x04" + bytes([density & 0xFF])
    buf += b"\x1f\x11" + bytes([media & 0xFF])
    width_bytes = (page.width + 7) // 8
    buf += b"\x1d\x76\x30\x00"
    buf += width_bytes.to_bytes(2, "little")
    buf += page.height.to_bytes(2, "little")
    buf += page.tobytes()
    buf += b"\x1f\xf0\x05\x00"
    buf += b"\x1f\xf0\x03\x00"
    return bytes(buf)
