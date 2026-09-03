# `m100` client

Python API for the Ponek M100 over Bluetooth SPP / USB serial. Proven
on firmware 0.1.1, serial `Q378…`, COM10.

```python
from m100 import M100Client

with M100Client("COM10") as printer:
    print(printer.status())
    printer.print_file("label.png")   # dark pixels burn
```

CLI (from the repo, after `pip install -e .`):

```
python -m m100 COM10 status
python -m m100 COM10 test
python -m m100 COM10 print path\to\image.png
```

Designer (keeps the printer connection open and prints the canvas):

```
python -m m100 COM10 serve
```

Opens http://127.0.0.1:8765/ — add text or an image, then Print.

`print_image` fits the bitmap into 40×30 mm at 203 DPI, shifts it 3.5 mm
right onto the 384 px head, and sends an M110 `GS v 0` job. It does not
auto-locate; that wasted the next sticker.
