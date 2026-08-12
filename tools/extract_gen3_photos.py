#!/usr/bin/env python3
"""Cut the GreenStar 3 2630 evidence out of the cab photographs.

Two kinds of image come out of this, used for two different jobs.

The button crops go inline in a step, at the size of a word, so the eye can
match the instruction against the glass without leaving the sentence. The whole
screens go behind them, one per step, so somebody who is unsure can look at the
real thing and see that the page is describing their display and not a
different one.

They come from photographs of a working combine rather than from a manual, so
they are the strongest evidence in this guide: not what the display is
documented to do, but what it actually showed on the day.
"""

import pathlib

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

SRC = pathlib.Path("/root/.claude/uploads/7a096789-f953-5630-8f5c-81fa45bf776a")
OUT = pathlib.Path("/workspace/ofpe/assets/photos/john_deere_gs3_2630")

PHOTOS = {
    "run_page": "2ca73cad-IMG_2446.HEIC",
    "menu": "d997b41b-IMG_2447.HEIC",
    "display_main": "dfabd381-IMG_2448.HEIC",
    "diagnostics": "54d6cfcb-IMG_2449.HEIC",
    "about": "38006fb5-IMG_2450.HEIC",
}

# Fractions of each photograph, read off the images themselves.
CROPS = {
    "btn_menu": ("run_page", (0.770, 0.808, 0.850, 0.862)),
    "btn_display": ("menu", (0.645, 0.198, 0.845, 0.300)),
    "btn_diagnostics": ("display_main", (0.728, 0.572, 0.815, 0.676)),
    "btn_about": ("about", (0.540, 0.228, 0.680, 0.290)),
    "the_answer": ("about", (0.290, 0.758, 0.570, 0.860)),
}

# A phone photograph of a screen is far more resolution than anyone needs and
# would bloat a page meant to open over a field data connection.
SCREEN_WIDTH = 1180
SCREEN_QUALITY = 74


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    loaded = {}

    for name, filename in PHOTOS.items():
        image = Image.open(SRC / filename).convert("RGB")
        loaded[name] = image
        shrunk = image.copy()
        shrunk.thumbnail((SCREEN_WIDTH, SCREEN_WIDTH), Image.LANCZOS)
        path = OUT / f"{name}.jpg"
        shrunk.save(path, quality=SCREEN_QUALITY, optimize=True, progressive=True)
        print(f"{path.name:22s} {str(shrunk.size):12s} {path.stat().st_size // 1024:4d} KB")

    for name, (source, (left, top, right, bottom)) in CROPS.items():
        image = loaded[source]
        width, height = image.size
        crop = image.crop((int(left * width), int(top * height),
                           int(right * width), int(bottom * height)))
        # Buttons are read at about 40 px tall in a line of text; twice that
        # keeps them sharp on a phone without carrying a photograph's weight.
        crop.thumbnail((520, 520), Image.LANCZOS)
        path = OUT / f"{name}.jpg"
        crop.save(path, quality=88, optimize=True)
        print(f"{path.name:22s} {str(crop.size):12s} {path.stat().st_size // 1024:4d} KB")

    total = sum(f.stat().st_size for f in OUT.iterdir())
    print(f"\n{len(list(OUT.iterdir()))} files, {total / 1024:.0f} KB total -> {OUT}")


if __name__ == "__main__":
    main()
