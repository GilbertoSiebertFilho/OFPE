#!/usr/bin/env python3
"""Cut the John Deere Gen 4 (4240) evidence out of the user's photographs.

Same two jobs as the GreenStar 3 and IntelliView IV sets: button crops that sit
inline in a step at the size of a word, and whole screens behind them for
anybody who wants to check the page against their own display.

The photographs are in a PDF the user assembled, "JD swather monitor 4240":
a 4240 in a swather, naming a track, choosing its field and typing the four
coordinates through to the finished line. Pass the PDF as the first argument
if it has moved.

Only pages 8 to 18 are used. Pages 1 to 7 of that PDF are frames of somebody
else's YouTube video -- the screens before the method grid -- and are not
reproduced here; the steps they cover are written as text.
"""

import io
import pathlib
import sys

import pymupdf
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                   r"\\files.win.olds\staff\gsiebertfilho\Downloads"
                   r"\JD swather monitor 4240 (1).pdf")
OUT = ROOT / "assets" / "photos" / "john_deere_gen4"

# (page, image index on that page) -- pages count from 1 as a PDF viewer does.
PHOTOS = {
    "new_track": (8, 0),
    "rename_press": (9, 0),
    "rename_keyboard": (10, 0),
    "field_press": (11, 0),
    "select_field": (12, 0),
    "select_field_done": (13, 0),
    "create_track_empty": (14, 0),
    "point_a_lat": (15, 0),
    "point_a_lon": (16, 0),
    "point_b_press": (16, 1),
    "point_b_lon": (17, 0),
    "create_track_filled": (17, 1),
    "guidance_page": (18, 0),
}

# Photographs a button is cut from but which no step shows whole.
CUT_FROM_ONLY = {"rename_press", "select_field", "point_b_press"}

# Fractions of each photograph, read off the images themselves.
CROPS = {
    "btn_track_name": ("new_track", (0.205, 0.200, 0.595, 0.340)),
    "btn_field": ("new_track", (0.140, 0.390, 0.490, 0.530)),
    "btn_ok_new_track": ("new_track", (0.715, 0.820, 0.875, 0.890)),
    "btn_client_farm_field": ("select_field_done", (0.125, 0.180, 0.395, 0.580)),
    "btn_point_boxes": ("create_track_empty", (0.160, 0.340, 0.830, 0.680)),
    "note_latitude": ("point_a_lat", (0.185, 0.290, 0.375, 0.540)),
    "btn_plus_minus": ("point_a_lon", (0.470, 0.720, 0.600, 0.825)),
    "note_longitude": ("point_a_lon", (0.190, 0.270, 0.390, 0.600)),
    "btn_ok_filled": ("create_track_filled", (0.685, 0.825, 0.850, 0.900)),
    "guidance_panel": ("guidance_page", (0.755, 0.200, 0.935, 0.400)),
}

SCREEN_WIDTH = 1180
SCREEN_QUALITY = 78


def load(doc, page: int, index: int) -> Image.Image:
    xref = doc[page - 1].get_images(full=True)[index][0]
    return Image.open(io.BytesIO(doc.extract_image(xref)["image"])).convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(SRC)
    loaded = {name: load(doc, page, index) for name, (page, index) in PHOTOS.items()}

    # Start clean, so a crop that was renamed or dropped does not linger.
    for old in OUT.glob("*.jpg"):
        old.unlink()

    for name, image in loaded.items():
        if name in CUT_FROM_ONLY:
            continue
        shrunk = image.copy()
        shrunk.thumbnail((SCREEN_WIDTH, SCREEN_WIDTH), Image.LANCZOS)
        path = OUT / f"{name}.jpg"
        shrunk.save(path, quality=SCREEN_QUALITY, optimize=True, progressive=True)
        print(f"{path.name:26s} {str(shrunk.size):12s} {path.stat().st_size // 1024:4d} KB")

    for name, (source, (left, top, right, bottom)) in CROPS.items():
        image = loaded[source]
        width, height = image.size
        crop = image.crop((int(left * width), int(top * height),
                           int(right * width), int(bottom * height)))
        crop.thumbnail((520, 520), Image.LANCZOS)
        path = OUT / f"{name}.jpg"
        crop.save(path, quality=88, optimize=True)
        print(f"{path.name:26s} {str(crop.size):12s} {path.stat().st_size // 1024:4d} KB")

    total = sum(f.stat().st_size for f in OUT.iterdir())
    print(f"\n{len(list(OUT.iterdir()))} files, {total / 1024:.0f} KB total -> {OUT}")


if __name__ == "__main__":
    main()
