#!/usr/bin/env python3
"""Cut the New Holland IntelliView IV evidence out of the cab photographs.

Same two jobs as the GreenStar 3 set (tools/extract_gen3_photos.py): button
crops that sit inline in a step at the size of a word, and whole screens behind
them for anybody who wants to check the page against their own display.

The photographs were taken on a New Holland combine in central Alberta on
11 September 2026 -- 88 of them, covering an AB line typed in as coordinates,
the same line brought in off a stick as ISOXML, and the yield data taken off.
They live in a shared Google Drive folder; pass another folder as the first
argument if they have moved.

One photo is altered: the FARM run page shows the operator's name, which is
blurred before it is saved. Nothing else is touched.
"""

import pathlib
import sys

import pillow_heif
from PIL import Image, ImageFilter, ImageOps

pillow_heif.register_heif_opener()

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                   r"G:\My Drive\Pictures New Holland Monitor Intelliview 4")
OUT = ROOT / "assets" / "photos" / "new_holland_intelliview_iv"

PHOTOS = {
    # Typing an AB line in as latitude and longitude
    "farm_page": "IMG_3024.HEIC",
    "grower_menu": "IMG_3025.HEIC",
    "gps_page": "IMG_3080.HEIC",
    "swath_type": "IMG_3035.HEIC",
    "recorder_new": "IMG_3082.HEIC",
    "ready_a": "IMG_3084.HEIC",
    "no_dgps": "IMG_3041.HEIC",
    "lat_a": "IMG_3038.HEIC",
    "lon_a": "IMG_3039.HEIC",
    "lat_b": "IMG_3088.HEIC",
    "swath_source": "IMG_3090.HEIC",
    "line_ready": "IMG_3092.HEIC",
    "swath_select_menu": "IMG_3047.HEIC",
    "info": "IMG_3050.HEIC",
    "map_line": "IMG_3094.HEIC",
    # Bringing the line in off a stick as ISOXML
    "sms_export": "IMG_3095.HEIC",
    "usb_port": "IMG_3067.HEIC",
    "main_menu": "IMG_3054.HEIC",
    "import_tab": "IMG_3059.HEIC",
    "source_isoxml": "IMG_3096.HEIC",
    "data_type_import": "IMG_3098.HEIC",
    "gff_file": "IMG_3102.HEIC",
    "confirm_import": "IMG_3104.HEIC",
    "import_complete": "IMG_3106.HEIC",
    "copy_info": "IMG_3108.HEIC",
    "copy_failed": "IMG_3109.HEIC",
    # Taking the work data off on a stick
    "export_page": "IMG_3068.HEIC",
    "export_greyed": "IMG_3063.HEIC",   # only cut from, never shown
    "target_list": "IMG_3070.HEIC",
    "data_type_export": "IMG_3071.HEIC",
    "confirm_export": "IMG_3074.HEIC",
    "export_complete": "IMG_3076.HEIC",
    "shutdown": "IMG_3079.HEIC",
}

# Photographs a button is cut from but which no step shows whole.
CUT_FROM_ONLY = {"export_greyed"}

# Blurred before anything is cut or saved. (photo, box as fractions)
REDACT = {
    "farm_page": [(0.612, 0.540, 0.888, 0.610)],  # the Operator box: a name
}

# Fractions of each photograph, read off the images themselves.
CROPS = {
    "btn_tab_farm": ("gps_page", (0.345, 0.820, 0.460, 0.900)),
    "btn_grower_menu": ("grower_menu", (0.375, 0.360, 0.935, 0.700)),
    "btn_tab_gps": ("farm_page", (0.425, 0.810, 0.535, 0.875)),
    "btn_type_straight": ("swath_type", (0.445, 0.205, 0.830, 0.335)),
    "btn_new": ("recorder_new", (0.395, 0.475, 0.840, 0.645)),
    "btn_enter_a": ("ready_a", (0.700, 0.795, 0.845, 0.885)),
    "warn_nodgps": ("no_dgps", (0.400, 0.235, 0.860, 0.520)),
    "btn_keypad": ("lat_a", (0.320, 0.600, 0.775, 0.805)),
    "btn_enter_b": ("swath_source", (0.710, 0.640, 0.855, 0.740)),
    "btn_intelliview": ("swath_source", (0.410, 0.280, 0.835, 0.405)),
    "btn_swath_select": ("line_ready", (0.540, 0.625, 0.700, 0.715)),
    "btn_swath_menu": ("swath_select_menu", (0.370, 0.290, 0.845, 0.765)),
    "btn_back": ("gps_page", (0.135, 0.820, 0.250, 0.895)),
    "btn_data_mgmt": ("main_menu", (0.680, 0.250, 0.840, 0.390)),
    "btn_tab_import2": ("export_greyed", (0.630, 0.750, 0.725, 0.820)),
    "btn_src_isoxml": ("source_isoxml", (0.450, 0.310, 0.865, 0.455)),
    "btn_dt_guidance": ("data_type_export", (0.615, 0.445, 0.810, 0.515)),
    "gff_isoxml": ("gff_file", (0.455, 0.455, 0.895, 0.700)),
    "btn_import_top": ("gff_file", (0.680, 0.355, 0.900, 0.440)),
    "btn_import_confirm": ("confirm_import", (0.405, 0.740, 0.560, 0.810)),
    "note_cn1": ("import_complete", (0.430, 0.470, 0.750, 0.560)),
    "btn_copy": ("import_complete", (0.700, 0.745, 0.830, 0.795)),
    "btn_yes": ("copy_info", (0.420, 0.805, 0.565, 0.855)),
    "sms_v3": ("sms_export", (0.505, 0.115, 0.770, 0.310)),
    "btn_tab_export": ("source_isoxml", (0.750, 0.790, 0.835, 0.850)),
    "btn_dt_yield": ("data_type_export", (0.420, 0.580, 0.615, 0.645)),
    "btn_export_top": ("export_page", (0.640, 0.185, 0.910, 0.280)),
    "btn_export_confirm": ("confirm_export", (0.420, 0.705, 0.540, 0.770)),
}

# A phone photograph of a screen is far more resolution than anyone needs and
# would bloat a page meant to open over a field data connection.
SCREEN_WIDTH = 1180
SCREEN_QUALITY = 74


def redact(image: Image.Image, boxes) -> Image.Image:
    width, height = image.size
    for left, top, right, bottom in boxes:
        box = (int(left * width), int(top * height),
               int(right * width), int(bottom * height))
        patch = image.crop(box).filter(ImageFilter.GaussianBlur(radius=60))
        image.paste(patch, box)
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    loaded = {}
    for name, filename in PHOTOS.items():
        image = ImageOps.exif_transpose(Image.open(SRC / filename)).convert("RGB")
        loaded[name] = redact(image, REDACT.get(name, ()))

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
        # Buttons are read at about 40 px tall in a line of text; twice that
        # keeps them sharp on a phone without carrying a photograph's weight.
        crop.thumbnail((520, 520), Image.LANCZOS)
        path = OUT / f"{name}.jpg"
        crop.save(path, quality=88, optimize=True)
        print(f"{path.name:26s} {str(crop.size):12s} {path.stat().st_size // 1024:4d} KB")

    total = sum(f.stat().st_size for f in OUT.iterdir())
    print(f"\n{len(list(OUT.iterdir()))} files, {total / 1024:.0f} KB total -> {OUT}")


if __name__ == "__main__":
    main()
