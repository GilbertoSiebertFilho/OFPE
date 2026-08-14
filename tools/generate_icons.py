#!/usr/bin/env python3
"""
Draws the schematic monitor icons and the supporting flow figures used across
the platform: the wizard's display picker, the procedure cards and the
per-display handbooks.

These are our own schematic drawings of the terminal's physical shape: screen
proportion, physical keys, rotary encoder. They do not reproduce manufacturers'
logos, figurative marks or photographs; model names appear as text reference
only.

Two variants come out of one source:

    assets/icons/*.png       with a caption, for print and documents
    assets/icons/ui/*.png    caption-free, for the web interface, where the
                             model name is already real text beside the image

Usage:  python3 tools/generate_icons.py
"""

from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

SS = 3  # supersampling
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons")

# ----------------------------------------------------------------- palette --
BG          = (255, 255, 255, 0)
BEZEL       = (38, 43, 49)
BEZEL_EDGE  = (18, 21, 24)
BEZEL_HI    = (74, 82, 90)
SCREEN_BG   = (13, 22, 28)
SCREEN_SKY  = (22, 38, 48)
FIELD       = (46, 104, 58)
FIELD_DARK  = (34, 78, 44)
ABLINE      = (245, 186, 66)
ABLINE_ACT  = (255, 233, 145)
VEHICLE     = (240, 245, 248)
STATUSBAR   = (30, 48, 60)
KEY         = (58, 64, 71)
KEY_EDGE    = (24, 27, 31)
TEXT_DARK   = (33, 37, 41)
TEXT_MID    = (108, 117, 125)
WHITE       = (255, 255, 255)


def _font(size: int, bold: bool = False):
    cands = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in cands:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def _center(d, xy, text, font, fill):
    x, y = xy
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((x - (r - l) / 2 - l, y - (b - t) / 2 - t), text, font=font, fill=fill)


# ------------------------------------------------------------ monitor screen
def _draw_screen(base_img, box, accent):
    """Draw the screen content on a sub-canvas and paste it clipped into the bezel.

    The clipping matters: the AB lines drawn in perspective diverge past the
    edges of the screen, and without it they would run out over the bezel.
    """
    bx0, by0, bx1, by1 = [int(round(v)) for v in box]
    sub = Image.new("RGBA", (bx1 - bx0, by1 - by0), SCREEN_BG)
    _paint_screen(ImageDraw.Draw(sub), (0, 0, bx1 - bx0, by1 - by0), accent)
    base_img.paste(sub, (bx0, by0))


def _paint_screen(d, box, accent):
    """Screen content: field, AB lines, vehicle, status bar."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0

    d.rectangle(box, fill=SCREEN_BG)
    # horizon / sky
    d.rectangle((x0, y0, x1, y0 + h * 0.30), fill=SCREEN_SKY)
    # field
    d.polygon(
        [(x0, y1), (x0, y0 + h * 0.30), (x1, y0 + h * 0.24), (x1, y1)],
        fill=FIELD_DARK,
    )
    d.polygon(
        [(x0 + w * 0.06, y1), (x0 + w * 0.20, y0 + h * 0.34),
         (x1 - w * 0.14, y0 + h * 0.30), (x1 - w * 0.02, y1)],
        fill=FIELD,
    )

    # AB lines in perspective
    for i in range(-3, 5):
        top_x = x0 + w * (0.50 + i * 0.055)
        bot_x = x0 + w * (0.50 + i * 0.20)
        if bot_x < x0 - w * 0.4 or bot_x > x1 + w * 0.4:
            continue
        col = ABLINE_ACT if i == 0 else ABLINE
        wid = max(1, int(3 * SS)) if i == 0 else max(1, int(1.4 * SS))
        d.line([(top_x, y0 + h * 0.32), (bot_x, y1)], fill=col, width=wid)

    # vehicle (triangle)
    cx, cy = x0 + w * 0.50, y0 + h * 0.74
    s = w * 0.075
    d.polygon([(cx, cy - s), (cx - s * 0.78, cy + s * 0.72), (cx + s * 0.78, cy + s * 0.72)],
              fill=VEHICLE)

    # top status bar
    d.rectangle((x0, y0, x1, y0 + h * 0.115), fill=STATUSBAR)
    d.rectangle((x0, y0, x0 + w * 0.16, y0 + h * 0.115), fill=accent)
    for i in range(3):
        bx = x1 - w * (0.07 + i * 0.055)
        d.rectangle((bx, y0 + h * 0.035, bx + w * 0.028, y0 + h * 0.082), fill=(150, 165, 175))


def draw_monitor(filename, label, sublabel, aspect=(16, 9), keys_right=0,
                 keys_bottom=0, rotary=False, accent=(60, 130, 200),
                 caption=True, outdir=None):
    """Draw a schematic terminal.

    caption=True  -> with a caption (model name plus specs). For print and
                     for documents that carry the picture alone.
    caption=False -> the terminal alone, filling the full height. Used by the
                     web interface, where the model name is already real text
                     beside the image; repeating it inside the picture would
                     duplicate the information.

    Cropping the caption in CSS was tried first and abandoned: the caption sits
    directly below the bezel, and the bezel's height moves with the screen
    aspect ratio, so no fixed crop is correct for every terminal.
    """
    W, H = 380 * SS, 300 * SS
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)

    margin_x = 18 * SS
    top = 14 * SS
    caption_h = 46 * SS if caption else 14 * SS
    avail_w = W - 2 * margin_x
    avail_h = H - top - caption_h

    key_col_w = (30 * SS) if keys_right else 0
    key_row_h = (24 * SS) if keys_bottom else 0
    rot_w = (30 * SS) if rotary else 0

    pad = 9 * SS
    # usable screen area inside the bezel
    inner_w = avail_w - key_col_w - rot_w - 2 * pad
    inner_h = avail_h - key_row_h - 2 * pad
    ar = aspect[0] / aspect[1]
    sw = inner_w
    sh = sw / ar
    if sh > inner_h:
        sh = inner_h
        sw = sh * ar

    bez_w = sw + 2 * pad + key_col_w + rot_w
    bez_h = sh + 2 * pad + key_row_h
    bx0 = (W - bez_w) / 2
    by0 = top + (avail_h - bez_h) / 2
    bx1, by1 = bx0 + bez_w, by0 + bez_h

    # drop shadow
    d.rounded_rectangle((bx0 + 3 * SS, by0 + 4 * SS, bx1 + 3 * SS, by1 + 4 * SS),
                        radius=9 * SS, fill=(0, 0, 0, 38))
    # bezel
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=9 * SS,
                        fill=BEZEL, outline=BEZEL_EDGE, width=max(1, int(1.6 * SS)))
    d.line((bx0 + 8 * SS, by0 + 1.6 * SS, bx1 - 8 * SS, by0 + 1.6 * SS),
           fill=BEZEL_HI, width=max(1, int(1.2 * SS)))

    sx0 = bx0 + pad
    sy0 = by0 + pad
    _draw_screen(img, (sx0, sy0, sx0 + sw, sy0 + sh), accent)
    d.rectangle((sx0, sy0, sx0 + sw, sy0 + sh), outline=(8, 11, 14),
                width=max(1, int(1.2 * SS)))

    # side keys (softkeys)
    if keys_right:
        kx = sx0 + sw + 6 * SS
        kw = 18 * SS
        gap = sh / keys_right
        for i in range(keys_right):
            ky = sy0 + i * gap + gap * 0.22
            d.rounded_rectangle((kx, ky, kx + kw, ky + gap * 0.56), radius=3 * SS,
                                fill=KEY, outline=KEY_EDGE, width=max(1, int(SS)))

    # rotary encoder
    if rotary:
        rx = bx1 - 20 * SS
        ry = by0 + bez_h * 0.70
        r = 11 * SS
        d.ellipse((rx - r, ry - r, rx + r, ry + r), fill=KEY,
                  outline=KEY_EDGE, width=max(1, int(1.4 * SS)))
        d.ellipse((rx - r * 0.42, ry - r * 0.42, rx + r * 0.42, ry + r * 0.42),
                  fill=(88, 96, 105))

    # bottom keys
    if keys_bottom:
        ky = sy0 + sh + 6 * SS
        gap = sw / keys_bottom
        for i in range(keys_bottom):
            kx = sx0 + i * gap + gap * 0.24
            d.rounded_rectangle((kx, ky, kx + gap * 0.52, ky + 12 * SS), radius=3 * SS,
                                fill=KEY, outline=KEY_EDGE, width=max(1, int(SS)))

    # caption
    if caption:
        _center(d, (W / 2, by1 + 16 * SS), label, _font(17 * SS, bold=True), TEXT_DARK)
        _center(d, (W / 2, by1 + 34 * SS), sublabel, _font(13 * SS), TEXT_MID)

    img = img.resize((W // SS, H // SS), Image.LANCZOS)
    destination = outdir or OUT
    os.makedirs(destination, exist_ok=True)
    img.save(os.path.join(destination, filename))
    return filename


# --------------------------------------------------------- process figures --
def _folder(d, x, y, w, h, color=(240, 190, 92), edge=(196, 148, 58)):
    tab_w = w * 0.42
    d.polygon([(x, y + h * 0.16), (x + tab_w * 0.82, y + h * 0.16),
               (x + tab_w, y), (x + w, y), (x + w, y + h), (x, y + h)],
              fill=color, outline=edge)


def fig_folder_structure(filename="fig_folder_structure.png"):
    """The folder layout a display expects on a USB stick, as one picture."""
    W, H = 620 * SS, 300 * SS
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    f_t = _font(17 * SS, bold=True)
    f = _font(14 * SS)
    f_s = _font(12 * SS)

    d.text((22 * SS, 16 * SS), "Folder structure on the USB stick (drive root)",
           font=f_t, fill=TEXT_DARK)
    d.line((22 * SS, 40 * SS, W - 22 * SS, 40 * SS), fill=(206, 212, 218), width=max(1, int(SS)))

    nodes = [
        (0, "USB DRIVE (FAT32)", "format FAT32, MBR partition", (176, 190, 200)),
        (1, "Rx", "prescriptions .shp + .shx + .dbf + .prj", (240, 190, 92)),
        (1, "AgData\\Prescriptions", "prescriptions (Precision-IQ)", (240, 190, 92)),
        (1, "TASKDATA", "TASKDATA.XML + .BIN  (ISOXML)", (240, 190, 92)),
        (1, "GS3_2630\\<Profile>\\RCD", "recorded data (GreenStar 3)", (240, 190, 92)),
        (1, "JD-Data", "exported work data (Gen 4 / G5)", (240, 190, 92)),
    ]
    y = 58 * SS
    for depth, name, desc, col in nodes:
        x = 30 * SS + depth * 34 * SS
        if depth > 0:
            d.line((44 * SS, y - 14 * SS, 44 * SS, y + 11 * SS), fill=(173, 181, 189),
                   width=max(1, int(1.4 * SS)))
            d.line((44 * SS, y + 11 * SS, x + 2 * SS, y + 11 * SS), fill=(173, 181, 189),
                   width=max(1, int(1.4 * SS)))
        _folder(d, x + 6 * SS, y, 26 * SS, 21 * SS, color=col)
        d.text((x + 40 * SS, y + 1 * SS), name, font=f, fill=TEXT_DARK)
        d.text((x + 40 * SS, y + 19 * SS), desc, font=f_s, fill=TEXT_MID)
        y += 39 * SS

    img = img.resize((W // SS, H // SS), Image.LANCZOS)
    img.save(os.path.join(OUT, filename))
    return filename


def _chip(d, x, y, w, h, title, sub, fill, edge, f_t, f_s):
    d.rounded_rectangle((x, y, x + w, y + h), radius=8 * SS, fill=fill,
                        outline=edge, width=max(1, int(1.6 * SS)))
    _center(d, (x + w / 2, y + h * 0.40), title, f_t, TEXT_DARK)
    _center(d, (x + w / 2, y + h * 0.68), sub, f_s, TEXT_MID)


def _arrow(d, x0, y, x1, color=(73, 105, 137), label=None, font=None, label_y=None):
    d.line((x0, y, x1 - 9 * SS, y), fill=color, width=max(1, int(2.6 * SS)))
    d.polygon([(x1, y), (x1 - 11 * SS, y - 6 * SS), (x1 - 11 * SS, y + 6 * SS)], fill=color)
    if label:
        _center(d, ((x0 + x1) / 2, label_y), label, font, color)


def fig_flow(filename, title_text, stages):
    """A left-to-right flow diagram: office, stick, machine."""
    W, H = 720 * SS, 178 * SS
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    f_t = _font(15 * SS, bold=True)
    f_c = _font(13 * SS, bold=True)
    f_s = _font(11 * SS)
    f_a = _font(11 * SS, bold=True)

    mx = 20 * SS
    d.text((mx, 13 * SS), title_text, font=f_t, fill=TEXT_DARK)
    d.line((mx, 36 * SS, W - mx, 36 * SS), fill=(206, 212, 218), width=max(1, int(SS)))

    n = len(stages)
    cw = 148 * SS
    gap = (W - 2 * mx - n * cw) / max(1, n - 1)
    y = 78 * SS          # top of the cards
    ch = 72 * SS
    lbl_y = 58 * SS      # the arrow label sits ABOVE the row of cards
    palette = [((226, 240, 250), (108, 160, 200)), ((233, 246, 233), (120, 175, 120)),
               ((253, 243, 224), (216, 170, 84)), ((240, 236, 250), (150, 135, 200)),
               ((235, 245, 247), (110, 165, 180))]
    for i, (title, sub, arrow_lbl) in enumerate(stages):
        x = mx + i * (cw + gap)
        fill, edge = palette[i % len(palette)]
        _chip(d, x, y, cw, ch, title, sub, fill, edge, f_c, f_s)
        if i < n - 1:
            _arrow(d, x + cw + 5 * SS, y + ch / 2, x + cw + gap - 5 * SS,
                   label=arrow_lbl, font=f_a, label_y=lbl_y)

    img = img.resize((W // SS, H // SS), Image.LANCZOS)
    img.save(os.path.join(OUT, filename))
    return filename


# ----------------------------------------------------------------------- main
# Sub-labels use neutral technical shorthand ("touch", "ISOBUS", inches and
# screen ratio) so that one set of drawings serves both deliverables without
# maintaining two of everything.
MONITORS = [
    # (filename, label, sub-label, aspect, keys_right, keys_bottom, rotary, accent)
    ("jd_gs3_2630.png",      "GreenStar 3 2630",   "10.4\"  ·  4:3  ·  touch + keys",
     (4, 3), 6, 0, False, (86, 145, 60)),
    ("jd_gen4.png",          "Gen 4  (4240/4600/4640)", "10.1\"  ·  16:9  ·  touch",
     (16, 9), 0, 0, False, (86, 145, 60)),
    ("jd_g5.png",            "G5  (G5e/G5/G5Plus)", "12.8\"  ·  16:9  ·  touch",
     (16, 9), 0, 0, False, (86, 145, 60)),
    ("cih_afs_pro700.png",   "AFS Pro 700",        "10.4\"  ·  4:3  ·  encoder + keys",
     (4, 3), 5, 0, True, (176, 58, 46)),
    ("cih_afs_pro1200.png",  "AFS Pro 1200",       "12.1\"  ·  16:10  ·  touch",
     (16, 10), 0, 0, False, (176, 58, 46)),
    ("nh_intelliview4.png",  "IntelliView IV",     "10.4\"  ·  4:3  ·  encoder + keys",
     (4, 3), 5, 0, True, (52, 106, 168)),
    ("nh_intelliview12.png", "IntelliView 12",     "12.1\"  ·  16:10  ·  touch",
     (16, 10), 0, 0, False, (52, 106, 168)),
    ("trimble_gfx750.png",   "GFX-750",            "10.1\"  ·  16:9  ·  bottom keys",
     (16, 9), 0, 4, False, (0, 118, 168)),
    ("trimble_gfx1060.png",  "GFX-1060 / GFX-1260", "10\" & 12\"  ·  16:9  ·  touch",
     (16, 9), 0, 0, False, (0, 118, 168)),
    ("trimble_tmx2050.png",  "TMX-2050",           "12.1\"  ·  16:10  ·  touch",
     (16, 10), 0, 0, False, (0, 118, 168)),
    ("trimble_fmx.png",      "FmX / CFX-750",      "12.1\" & 8\"  ·  4:3  ·  AgGPS",
     (4, 3), 0, 0, False, (0, 118, 168)),
    ("agleader_incommand.png", "InCommand 800 / 1200", "8\" & 12.1\"  ·  touch",
     (16, 10), 0, 0, False, (222, 138, 40)),
    ("raven_viper4.png",     "Viper 4 / Viper 4+",  "12.1\"  ·  touch",
     (16, 10), 0, 0, False, (196, 62, 52)),
    ("topcon_x35.png",       "X35 / XD+ (Horizon)", "12.1\"  ·  touch  ·  ISOBUS",
     (16, 10), 0, 0, False, (24, 96, 158)),
    ("fendt_varioterminal.png", "Varioterminal / FendtONE", "10.4\" & 12\"  ·  ISOBUS",
     (4, 3), 4, 0, True, (72, 130, 60)),
    # --- added for the procedure platform ------------------------------------
    ("claas_cemis1200.png",  "CEMIS 1200",         "12\"  ·  16:9  ·  touch  ·  ISOBUS",
     (16, 9), 0, 0, False, (146, 168, 46)),
    ("claas_s10.png",        "S10 / GPS PILOT",    "10.4\"  ·  4:3  ·  touch + keys",
     (4, 3), 4, 0, False, (146, 168, 46)),
    ("valtra_smarttouch.png", "SmartTouch",        "9\"  ·  16:9  ·  touch  ·  ISOBUS",
     (16, 9), 0, 0, False, (52, 78, 132)),
    ("mf_datatronic.png",    "Datatronic 5",       "9\"  ·  16:9  ·  touch  ·  ISOBUS",
     (16, 9), 0, 0, False, (176, 42, 46)),
    ("kverneland_isomatch.png", "IsoMatch Tellus", "12.1\"  ·  touch  ·  ISOBUS",
     (16, 10), 0, 0, False, (60, 108, 62)),
    ("mueller_touch1200.png", "TOUCH 1200 / 800",  "12.1\" & 8\"  ·  TRACK-Leader",
     (16, 10), 0, 4, False, (66, 88, 112)),
    ("pp_2020.png",          "20|20",              "12.1\"  ·  touch  ·  SeedSense",
     (16, 10), 0, 0, False, (40, 46, 54)),
    ("teejet_matrix.png",    "Matrix Pro GS",      "8\" & 10.4\"  ·  touch + keys",
     (4, 3), 0, 5, False, (196, 128, 34)),
    ("agopengps.png",        "AgOpenGPS",          "tablet / PC  ·  open source",
     (16, 10), 0, 0, False, (86, 122, 168)),
    ("generic_isobus.png",   "ISOBUS terminal",    "any TC-BAS terminal  ·  ISOXML",
     (16, 10), 0, 0, False, (108, 117, 125)),
    # --- added from the producer survey --------------------------------------
    ("bourgault_icon.png",   "iCon",               "iPad  ·  wireless  ·  air seeder",
     (4, 3), 0, 0, False, (86, 128, 52)),
    ("outback_rebel.png",    "Rebel",              "touch  ·  guidance",
     (4, 3), 0, 0, False, (208, 110, 36)),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    written = []
    ui_dir = os.path.join(OUT, "ui")
    for args in MONITORS:
        fn, label, sub, aspect, kr, kb, rot, acc = args
        written.append(draw_monitor(fn, label, sub, aspect=aspect, keys_right=kr,
                                    keys_bottom=kb, rotary=rot, accent=acc))
        # The same artwork without a caption, for the web interface.
        draw_monitor(fn, label, sub, aspect=aspect, keys_right=kr,
                     keys_bottom=kb, rotary=rot, accent=acc,
                     caption=False, outdir=ui_dir)

    written.append(fig_folder_structure())

    # The three ways data ever moves between an office and a machine.
    written.append(fig_flow(
        "fig_flow_office_to_monitor.png",
        "Flow A - Sending files from the office TO the monitor (via USB stick)",
        [("1. OFFICE", "build Rx / AB lines", "export"),
         ("2. USB STICK", "right folder + FAT32", "carry to field"),
         ("3. MONITOR", "Import / File Manager", "select"),
         ("4. WORK", "attach to the field", None)],
    ))

    written.append(fig_flow(
        "fig_flow_monitor_to_office.png",
        "Flow B - Getting the recorded data FROM the monitor to the office",
        [("1. MONITOR", "end the job first", "export"),
         ("2. USB STICK", "recorded data", "carry to PC"),
         ("3. SOFTWARE", "import and process", "publish"),
         ("4. CLOUD", "backup and analysis", None)],
    ))

    written.append(fig_flow(
        "fig_flow_cloud.png",
        "Flow C - Wireless transfer through the manufacturer's platform",
        [("1. PLATFORM", "manufacturer's web app", "send"),
         ("2. CLOUD", "account + machine", "modem / telematics"),
         ("3. MONITOR", "accept the transfer", None)],
    ))

    print("\n".join(written))
    print(f"\n{len(written)} files written to {OUT}")


if __name__ == "__main__":
    main()
