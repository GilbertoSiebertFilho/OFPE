#!/usr/bin/env python3
"""Build the OFPE Monitor Guide as one self-contained HTML page.

The guide needs no server: 341 procedures of built-in knowledge, no database,
no calculation. So it can be a single file that opens from a link on any phone
in any cab, with nothing installed. This script bakes the procedure data and
the terminal drawings into that file.
"""

import base64
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ofpe import catalog as cat, procedures as pr  # noqa: E402

OUT = ROOT / "OFPE-Guide.html"

# --------------------------------------------------------------------------- #
#  Data
# --------------------------------------------------------------------------- #

monitors, icons = [], {}
for key, m in cat.MONITORS.items():
    if not m.is_terminal:
        continue
    monitors.append({
        "key": key, "brand": m.brand, "model": m.model, "label": m.label,
        "aka": list(m.aka), "generations": m.generations,
        "equipment": list(m.equipment), "icon": m.icon,
        "vocab": m.guidance_vocabulary,
        "versions": [v.to_dict() for v in pr.versions_for(key)],
    })
    if m.icon not in icons:
        raw = (ROOT / "assets" / "icons" / "ui" / m.icon).read_bytes()
        icons[m.icon] = "data:image/png;base64," + base64.b64encode(raw).decode()

# The application icons a step can name. Embedded like everything else so the
# page keeps working with no network; keyed by the lower-cased on-screen label,
# which is exactly what a step's « » contains.
screen_icons, credits = {}, {}
for key in monitors:
    found = pr.icons_for(key["key"])
    if not found:
        continue
    folder = pr.folder_for(key["key"])
    table = {}
    for label, icon in found.items():
        path = ROOT / "assets" / "icons" / folder / icon.file
        table[label] = {
            "src": "data:image/png;base64," + base64.b64encode(
                path.read_bytes()).decode(),
            "code": icon.code,
        }
    screen_icons[key["key"]] = table
    credits[key["key"]] = pr.icon_credit(key["key"])

# The photographed walk-through for finding a software version. Embedded like
# everything else, because the whole point is that it opens in a cab with no
# signal. The photographs are the heaviest thing on the page and still cheap
# next to being unable to answer question three.
version_help = {}
for entry in monitors:
    help_ = pr.version_help_for(entry["key"])
    if not help_:
        continue
    photos = ROOT / "assets" / "photos" / help_.folder

    def _img(name: str) -> str:
        return "data:image/jpeg;base64," + base64.b64encode(
            (photos / name).read_bytes()).decode()

    version_help[entry["key"]] = {
        "field": help_.field_label,
        "example": help_.example,
        "readsAs": help_.reads_as,
        "evidence": help_.evidence,
        "alsoShows": list(help_.also_shows),
        "steps": [
            {
                "text": s.text,
                "button": _img(s.button) if s.button else "",
                "screen": _img(s.screen) if s.screen else "",
                "lookFor": s.look_for,
                "screenName": s.screen_name,
            }
            for s in help_.steps
        ],
    }

# Photographs for the answers somebody has actually shot in a cab. Keyed the
# same way a procedure is resolved, and indexed by step, because the walk-through
# owns those steps -- there is no second list to fall out of step with.
walk_photos = {}
for walk in pr.WALKTHROUGHS:
    shots = ROOT / "assets" / "photos" / walk.folder

    def _shot(name: str) -> str:
        return "data:image/jpeg;base64," + base64.b64encode(
            (shots / name).read_bytes()).decode()

    walk_photos["|".join((walk.monitor_key, walk.objective, walk.transport))] = {
        "evidence": walk.evidence,
        "steps": [
            {
                "button": _shot(s.button) if s.button else "",
                "screen": _shot(s.screen) if s.screen else "",
                "screenName": s.screen_name,
                "lookFor": s.look_for,
            }
            for s in walk.steps
        ],
    }

# Recorded speech, if any has been made. tools/render_voice.py renders every
# line the page can say to an MP3 named after the line itself, so the page
# never has to work out a file name -- it is handed the names here, and the
# two cannot drift apart. With no recordings the keys are simply absent and
# the page falls back to the phone's own speech engine, which is exactly what
# it did before any of this existed.
#
# The tone backend exists to test the player without model weights. Shipping
# a page that points at tones would be worse than shipping no audio at all,
# so it takes an environment variable to do it, deliberately, rather than a
# forgotten flag.
voice_dir = ROOT / "voice"
voice_manifest = voice_dir / "manifest.json"
voice_clips: dict[str, dict] = {}
voice_meta: dict[str, str] = {}
if voice_manifest.exists():
    _m = json.loads(voice_manifest.read_text())
    if pr.voice.shippable(_m, bool(os.environ.get("OFPE_FAKE_VOICE"))):
        voice_clips = _m.get("clips", {})
        voice_meta = {"dir": "voice/", "ext": "." + _m.get("format", "mp3"),
                      "model": _m.get("model", ""), "voice": _m.get("voice", "")}
    else:
        print(f"  voice/: {_m.get('backend')} recordings are not speech — "
              "not embedding (OFPE_FAKE_VOICE=1 overrides, for a test build)")


def clip_ids(steps) -> list[str]:
    """The recording for each step, or "" where none was made."""
    out = []
    for step in steps:
        spoken = pr.voice.spoken(step)
        clip = pr.voice.clip_id(spoken) if spoken else ""
        out.append(clip if clip in voice_clips else "")
    return out


procedures = []
for p in pr.PROCEDURES:
    d = p.to_dict()
    entry = {
        "m": d["monitor_key"], "o": d["objective"], "t": d["transport"],
        "v": d["version_keys"], "fmt": d["file_format"], "ext": d["extensions"],
        "path": d["media_path"], "fs": d["filesystem"], "plat": d["platform"],
        "min": d["minutes"], "pre": d["prerequisites"], "steps": d["steps"],
        "ok": d["verify"], "care": d["cautions"], "bad": d["common_errors"],
        "conf": d["confidence"], "src": d["sources"],
    }
    if voice_clips:
        entry["say"] = clip_ids(d["steps"])
    procedures.append(entry)

# "Step 4." is its own recording rather than part of the step's, so that the
# same sentence at position 2 of one procedure and position 7 of another is
# one file instead of two.
voice_numbers = []
if voice_clips:
    for n in range(1, pr.voice.longest_procedure() + 1):
        clip = pr.voice.clip_id(pr.voice.step_prefix(n))
        voice_numbers.append(clip if clip in voice_clips else "")

DATA = {
    "monitors": monitors,
    "icons": icons,
    "objectives": {k: {"label": o.label, "dir": o.direction.value,
                       "desc": o.description, "notFor": list(o.not_for)}
                   for k, o in pr.OBJECTIVES.items()},
    "objectiveLabels": {f"{m}|{o}": label
                        for (m, o), label in pr.OBJECTIVE_LABELS.items()},
    "outOfScope": {k: list(v) for k, v in pr.SCOPE_EXCLUSIONS.items()},
    "objectiveOrder": list(pr.OBJECTIVES),
    "directions": {d.value: d.label for d in pr.Direction},
    "transports": {t.value: {"label": t.label, "desc": t.description}
                   for t in pr.Transport},
    "equipment": {e.value: e.label for e in pr.EquipmentType},
    "confidence": {c.value: {"label": c.label, "desc": c.description}
                   for c in pr.Confidence},
    "procedures": procedures,
    "screenIcons": screen_icons,
    "versionHelp": version_help,
    "walkPhotos": walk_photos,
    "iconCredits": credits,
    "voice": voice_meta,
    "voiceNums": voice_numbers,
}

# --------------------------------------------------------------------------- #
#  Page
# --------------------------------------------------------------------------- #

CSS = r"""
/* Palette taken from the terminal drawings the page carries: the bezel
   graphite, the field green, and the amber of a guidance line. The accent is
   literally the colour of the thing this guide is about. Neutrals are biased
   green rather than the usual warm cream, so they sit with the artwork.
   Kept close to paper: this is read in a bright cab, off a phone held at
   arm's length, and a heavy ground makes the steps harder to pick out than a
   near-white one. */
:root {
  --ground:      #f6f7f3;
  --surface:     #ffffff;
  --surface-2:   #f0f2ec;
  --line:        #dde1d6;
  --line-soft:   #ebeee6;
  --ink:         #1a1f18;
  --ink-2:       #59614f;
  --ink-3:       #868e7f;
  --accent:      #8a5a00;      /* amber, darkened to hold contrast on paper */
  --accent-ink:  #ffffff;
  --accent-soft: #fdf6e7;
  --accent-line: #d9a233;
  --ok:          #1f6146;
  --ok-soft:     #eef6f1;
  --warn:        #8a5a00;
  --warn-soft:   #fdf6e7;
  --stop:        #99302a;
  --stop-soft:   #fcf0ee;
  --shadow:      0 1px 2px rgba(26,31,24,.04), 0 4px 14px rgba(26,31,24,.05);
  --step:  clamp(1rem, .96rem + .2vw, 1.09rem);
  --mono: ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:      #1b1f19;
    --surface:     #242923;
    --surface-2:   #2c322a;
    --line:        #3d443a;
    --line-soft:   #333a31;
    --ink:         #e9ede4;
    --ink-2:       #b2bba9;
    --ink-3:       #848d7d;
    --accent:      #f5ba42;
    --accent-ink:  #1a1403;
    --accent-soft: #2e2611;
    --accent-line: #f5ba42;
    --ok:          #6cc196;
    --ok-soft:     #14291f;
    --warn:        #e0ab54;
    --warn-soft:   #2c2411;
    --stop:        #e58a80;
    --stop-soft:   #2e1a18;
    --shadow:      0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.3);
  }
}
:root[data-theme="dark"] {
  --ground:#1b1f19; --surface:#242923; --surface-2:#2c322a; --line:#3d443a;
  --line-soft:#333a31; --ink:#e9ede4; --ink-2:#b2bba9; --ink-3:#848d7d;
  --accent:#f5ba42; --accent-ink:#1a1403; --accent-soft:#2e2611;
  --accent-line:#f5ba42; --ok:#6cc196; --ok-soft:#14291f; --warn:#e0ab54;
  --warn-soft:#2c2411; --stop:#e58a80; --stop-soft:#2e1a18;
  --shadow: 0 1px 2px rgba(0,0,0,.4), 0 6px 18px rgba(0,0,0,.3);
}

/* The page opens light whatever the phone is set to.
   A display guide is read outdoors, in a bright cab, often with the screen at
   arm's length -- and a phone left in dark mode by default was handing people
   a dark page in exactly the conditions a dark page is worst for. Following
   the system preference is the right default for most pages and the wrong one
   for this. Dark is still there for anyone who wants it, one press away, so
   this is a starting point rather than a decision taken away. */

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--ground); color: var(--ink);
  font-family: var(--sans); font-size: 16px; line-height: 1.55;
}
:focus-visible { outline: 3px solid var(--accent-line); outline-offset: 2px; border-radius: 4px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

.wrap { max-width: 760px; margin: 0 auto; padding: 0 18px 96px; }

/* ---------------------------------------------------------------- header */
header { padding: 30px 0 20px; }
h1 {
  margin: 0; font-size: clamp(1.55rem, 1.25rem + 1.4vw, 2.1rem);
  line-height: 1.15; letter-spacing: -.021em; font-weight: 680; text-wrap: balance;
}
.tagline { margin: 9px 0 0; color: var(--ink-2); max-width: 60ch; }
.rule { height: 3px; margin: 18px 0 0; border-radius: 2px;
  background: repeating-linear-gradient(90deg, var(--accent-line) 0 22px, transparent 22px 34px); }

/* Once the first question is answered the masthead shrinks out of the way --
   the answer is what you came for, not the title of the page. */
body.go header { padding: 18px 0 12px; }
body.go h1 { font-size: 1.16rem; letter-spacing: -.012em; }
body.go .tagline, body.go .rule { display: none; }
body.go .search { margin-top: 13px; }
body.go .search input { padding: 9px 13px; font-size: .92rem; }

.themebtn {
  position: absolute; top: 26px; right: 0; font: inherit; font-size: .8rem;
  cursor: pointer; padding: 7px 12px; min-height: 38px; border-radius: 99px;
  border: 1px solid var(--line); background: var(--surface); color: var(--ink-2);
}
.themebtn:hover { border-color: var(--accent-line); color: var(--ink); }
body.go .themebtn { top: 14px; }
header { position: relative; }

.search { margin-top: 20px; position: relative; }
.search input {
  width: 100%; font: inherit; font-size: 1rem; padding: 13px 15px;
  border: 1.5px solid var(--line); border-radius: 10px;
  background: var(--surface); color: var(--ink);
}
.search input::placeholder { color: var(--ink-3); }
.hits { margin-top: 6px; display: flex; flex-direction: column; gap: 4px; }
.hits:empty { display: none; }
.hits button {
  display: flex; align-items: center; gap: 11px; text-align: left;
  padding: 8px 11px; border: 1px solid var(--line); border-radius: 9px;
  background: var(--surface); color: var(--ink); font: inherit; cursor: pointer;
}
.hits button:hover { border-color: var(--accent-line); }
.hits img { width: 48px; aspect-ratio: 380/300; flex: none; }

/* ------------------------------------------------------------ breadcrumb */
/* Answered questions collapse to one line, so on a phone the screen shows
   the steps rather than the wizard that produced them. */
/* One way back, not five ways to delete an answer.
   The chips used to carry a × that cleared that step and everything after it:
   a small target, and an interaction you can get wrong with a glove on. A Back
   button is one press with an obvious meaning, so the answers beside it stop
   being controls and go back to being what they always were -- a reminder of
   where you are. */
.trail {
  display: flex; align-items: center; gap: 12px; margin: 0 0 4px;
  position: sticky; top: 0; z-index: 5; padding: 9px 0;
  background: var(--ground); border-bottom: 1px solid var(--line-soft);
}
.trail:empty { display: none; }
.backbtn {
  font: inherit; font-weight: 620; font-size: .88rem; cursor: pointer;
  padding: 9px 16px 9px 12px; min-height: 44px; flex: none;
  display: inline-flex; align-items: center; gap: 7px;
  border: 1.5px solid var(--line); border-radius: 99px;
  background: var(--surface); color: var(--ink);
}
.backbtn:hover { border-color: var(--accent-line); color: var(--accent); }
.backbtn svg { width: 15px; height: 15px; fill: currentColor; }
/* The end of the trail is the part you are working on, so when it does not
   fit, the start goes -- but a whole answer at a time. Sliding the line
   sideways under one ellipsis cuts words in half ("...ll off work data"),
   which costs a glance to decode; dropping "Combine harvester" entirely does
   not. Which crumbs survive is decided in fitCrumbs, after measuring. */
.crumbs {
  font-size: .84rem; color: var(--ink-3);
  flex: 1 1 auto; min-width: 0; overflow: hidden;
  display: flex; align-items: baseline; gap: 7px; white-space: nowrap;
}
.crumbs > * { flex: none; }
/* The last crumb is the one worth keeping, so it is also the only one allowed
   to shrink -- and it ellipsises at its end, where a cut reads as a cut. */
.crumbs > .now { flex: 0 1 auto; overflow: hidden; text-overflow: ellipsis; }
.crumbs .dot { opacity: .55; }

/* ----------------------------------------------------------------- steps */
.q { margin: 28px 0 0; }
.q[hidden] { display: none; }
.qhead { display: flex; align-items: baseline; gap: 11px; margin-bottom: 13px; }
.qnum {
  font-family: var(--mono); font-size: .78rem; font-weight: 700;
  color: var(--accent); letter-spacing: .06em; flex: none;
  padding-top: .18em;
}
.qtitle { margin: 0; font-size: 1.18rem; font-weight: 640; letter-spacing: -.012em; }
.qnote { margin: -6px 0 13px; color: var(--ink-3); font-size: .89rem; max-width: 58ch; }

.chips { display: flex; flex-wrap: wrap; gap: 9px; }
.chip {
  font: inherit; cursor: pointer; text-align: left;
  padding: 12px 17px; border-radius: 11px; min-height: 48px;
  border: 1.5px solid var(--line); background: var(--surface); color: var(--ink);
  display: flex; flex-direction: column; justify-content: center; gap: 2px;
}
.chip:hover { border-color: var(--accent-line); }
.chip .sub { font-size: .8rem; color: var(--ink-3); }
.chip .n { font-family: var(--mono); font-size: .76rem; color: var(--ink-3); }

/* The drawings all show the same green guidance screen, because that is what
   every one of these displays actually shows. So the model name leads and the
   drawing sits underneath at thumbnail size, where the bezel shape is the
   thing you match against the box in the cab. */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(152px, 1fr)); gap: 10px; }
.mcard {
  font: inherit; cursor: pointer; padding: 11px 11px 9px; border-radius: 11px;
  border: 1.5px solid var(--line); background: var(--surface); color: var(--ink);
  display: flex; flex-direction: column; gap: 2px; text-align: left;
}
.mcard:hover { border-color: var(--accent-line); }
.mcard img { width: 78px; aspect-ratio: 380/300; align-self: flex-end;
  margin-top: auto; padding-top: 10px; opacity: .92; }
.mcard .b { font-size: .71rem; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--ink-3); }
.mcard .m { font-size: .93rem; font-weight: 620; line-height: 1.27; letter-spacing: -.008em; }

.jobs { display: flex; flex-direction: column; gap: 20px; }
.jobgroup h3 {
  margin: 0 0 9px; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .1em; color: var(--ink-3); font-weight: 700;
  display: flex; align-items: center; gap: 10px;
}
.jobgroup h3::after { content: ""; flex: 1; height: 1px; background: var(--line-soft); }
.job {
  display: block; width: 100%; text-align: left; font: inherit; cursor: pointer;
  padding: 13px 16px; margin-bottom: 7px; border-radius: 10px;
  border: 1.5px solid var(--line); background: var(--surface); color: var(--ink);
}
.job:hover { border-color: var(--accent-line); }
.job b { display: block; font-size: 1rem; font-weight: 620; }
.job span { display: block; font-size: .85rem; color: var(--ink-3); margin-top: 2px; }

/* ---------------------------------------------------------------- result */
.result { margin-top: 30px; }
.result[hidden] { display: none; }
.card {
  border: 1.5px solid var(--line); border-radius: 14px;
  background: var(--surface); box-shadow: var(--shadow); overflow: hidden;
}
.chead {
  display: flex; gap: 17px; align-items: center; flex-wrap: wrap;
  padding: 18px 20px; background: var(--surface-2);
  border-bottom: 1.5px solid var(--line);
}
.chead img { width: 132px; aspect-ratio: 380/300; flex: none; }
.chead .t { flex: 1; min-width: 210px; }
.chead h2 { margin: 0; font-size: 1.3rem; font-weight: 660; letter-spacing: -.015em; text-wrap: balance; }
.chead p { margin: 3px 0 0; color: var(--ink-2); font-size: .9rem; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.tag {
  font-size: .73rem; font-weight: 640; padding: 3px 9px; border-radius: 99px;
  border: 1px solid var(--line); background: var(--surface); color: var(--ink-2);
}
.tag.ok { border-color: var(--ok); color: var(--ok); background: var(--ok-soft); }
.tag.check { border-color: var(--warn); color: var(--warn); background: var(--warn-soft); }

.body { padding: 20px; }
h4 {
  margin: 26px 0 11px; font-size: .74rem; text-transform: uppercase;
  letter-spacing: .1em; color: var(--ink-3); font-weight: 700;
}
h4:first-child { margin-top: 0; }

.facts {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(172px, 1fr));
  gap: 8px; margin: 0;
}
.facts > div {
  background: var(--surface); padding: 11px 14px;
  border: 1px solid var(--line); border-radius: 10px;
}
.facts dt { font-size: .69rem; text-transform: uppercase; letter-spacing: .08em; color: var(--ink-3); font-weight: 700; }
.facts dd { margin: 4px 0 0; font-weight: 600; font-size: .95rem; overflow-wrap: anywhere; }
.facts code {
  font-family: var(--mono); font-size: .87rem; font-weight: 600;
  background: var(--accent-soft); color: var(--ink); padding: 3px 7px;
  border-radius: 5px; display: inline-block; border: 1px solid var(--accent-line);
}

ol.steps { counter-reset: s; list-style: none; margin: 0; padding: 0; }
ol.steps li {
  counter-increment: s; position: relative; padding: 0 0 15px 44px;
  font-size: var(--step); line-height: 1.5;
}
ol.steps li::before {
  content: counter(s); position: absolute; left: 0; top: -1px;
  width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center;
  background: var(--accent); color: var(--accent-ink);
  font-family: var(--mono); font-size: .87rem; font-weight: 700;
}
ol.steps li:last-child { padding-bottom: 0; }

/* «Label» in a step is the exact wording on the display. Drawn as a key cap so
   the eye can jump straight to the word it has to find on the glass. */
.key {
  font-weight: 680; white-space: nowrap; padding: .09em .4em;
  margin: 0 .04em; border-radius: 5px; background: var(--surface-2);
  border: 1px solid var(--line); box-shadow: 0 1px 0 var(--line);
}
.note .key { background: var(--surface); }
.key.hasicon { display: inline-flex; align-items: center; gap: .3em;
  padding: .12em .45em .12em .3em; vertical-align: -.32em; }
/* The manual prints these as grey-on-white glyphs. On a dark ground they need
   lifting off the page, not inverting -- an inverted icon stops matching the
   display. So the cap keeps a light plate under it in both themes. */
.key.hasicon img { width: 1.55em; height: 1.55em; display: block;
  border-radius: 3px; background: #f4f5f1; }
/* A cap and the punctuation after it travel together (see keys()). The cap's
   own margin would leave the full stop floating away from it, so inside that
   pair it goes. */
.nb { white-space: nowrap; }
.nb .key { margin-right: 0; }

/* ------------------------------------------------------ reading it aloud */
/* Hands inside the machine, phone on the seat. The browser's own speech
   engine reads the steps out, which needs no install, no account and no
   signal -- the same constraints the rest of the page is built for. */
.saybar { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 16px; }
.saybtn {
  font: inherit; font-weight: 620; cursor: pointer; padding: 11px 17px;
  border-radius: 9px; min-height: 46px; display: inline-flex;
  align-items: center; gap: 9px;
  border: 1.5px solid var(--accent); background: var(--accent);
  color: var(--accent-ink);
}
.saybtn.quiet { background: var(--surface); color: var(--ink);
  border-color: var(--line); }
.saybtn.quiet:hover { border-color: var(--accent-line); }
.saybtn svg { width: 18px; height: 18px; flex: none; fill: currentColor; }
/* The step being read lights up, so a glance finds your place again. */
ol.steps li.saying { background: var(--accent-soft); border-radius: 9px;
  box-shadow: 0 0 0 8px var(--accent-soft); }
.saynote { font-size: .82rem; color: var(--ink-3); margin: -8px 0 16px; }

/* -------------------------------------------- what is not on screen yet */
/* The answer is the file and the steps. Everything else -- what to have ready,
   how to check, what goes wrong, where it came from -- is reference: needed
   sometimes, in the way always. So it collapses to a row you can open, with a
   count, which is enough to know whether it is worth opening. */
.more { display: flex; flex-direction: column; gap: 7px; margin-top: 22px; }
.more details {
  border: 1px solid var(--line); border-radius: 10px; background: var(--surface);
  overflow: hidden;
}
.more summary {
  cursor: pointer; list-style: none; padding: 12px 15px;
  display: flex; align-items: center; gap: 10px; font-size: .93rem;
}
.more summary::-webkit-details-marker { display: none; }
.more summary::before {
  content: "+"; font-family: var(--mono); font-weight: 700; color: var(--accent);
  width: 1em; text-align: center; flex: none;
}
.more details[open] summary::before { content: "\2013"; }
.more details[open] summary { border-bottom: 1px solid var(--line-soft); }
.more summary:hover { color: var(--accent); }
.more .n { margin-left: auto; color: var(--ink-3); font-size: .82rem;
  font-family: var(--mono); }
.more .inner { padding: 13px 15px 15px; }
.more ul { margin: 0; padding-left: 19px; }
.more li { margin-bottom: 8px; } .more li:last-child { margin-bottom: 0; }
.more .src { font-size: .84rem; color: var(--ink-2); }
.more .src p { margin: 0 0 7px; } .more .src p:last-child { margin: 0; }
/* A dot carries the tone the coloured panel used to. Quieter, same meaning. */
.more .dot { width: 8px; height: 8px; border-radius: 50%; flex: none;
  background: var(--ink-3); }
.more .dot.ok { background: var(--ok); }
.more .dot.care { background: var(--warn); }
.more .dot.stop { background: var(--stop); }
@media print {
  .more details { border: 0; break-inside: avoid; }
  .more summary { padding: 0; font-weight: 700; }
  .more summary::before, .more .n, .more .dot { display: none; }
  .more .inner { padding: 6px 0 12px; }
}

/* --------------------------------------------- an openable panel */
/* Question three is where people stall, so the answer lives inside the
   question rather than a page away. Closed by default: somebody who knows
   their version should not have to scroll past a walk-through to answer. */
.panel { margin: 14px 0 4px; border: 1px solid var(--line);
  border-radius: 11px; background: var(--surface); overflow: hidden; }
.panel > summary {
  cursor: pointer; padding: 14px 16px; font-weight: 620; list-style: none;
  display: flex; align-items: center; gap: 9px;
}
.panel[open] > summary { border-bottom: 1px solid var(--line-soft); }
.panel > summary:hover { color: var(--accent); }
.panel > summary::-webkit-details-marker { display: none; }
.panel > summary::before {
  content: "▸"; color: var(--accent); font-size: .9em; transition: transform .15s;
}
.panel[open] > summary::before { transform: rotate(90deg); }
.panel .vbody { padding: 16px; }
.panel .vbody > .qnote { margin: 0 0 16px; }
.panel .more { margin-top: 18px; }
ol.vsteps { counter-reset: v; list-style: none; margin: 0; padding: 0; }
ol.vsteps > li {
  counter-increment: v; position: relative; padding: 0 0 18px 44px;
  font-size: var(--step); line-height: 1.5;
}
ol.vsteps > li::before {
  content: counter(v); position: absolute; left: 0; top: -1px;
  width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center;
  background: var(--accent); color: var(--accent-ink);
  font-family: var(--mono); font-size: .87rem; font-weight: 700;
}
/* The button crop sits in the flow of the sentence at the size of a word:
   the eye matches it against the glass without leaving the instruction. */
.vbtn { display: block; margin: 9px 0 0; max-width: 210px; width: 100%;
  border: 1.5px solid var(--line); border-radius: 8px; background: #fff; }
.vshot {
  display: flex; gap: 9px; align-items: center; margin-top: 10px;
  padding: 8px 11px 8px 8px; border: 1px solid var(--line); border-radius: 9px;
  background: var(--surface-2); color: var(--ink-2); font: inherit;
  font-size: .84rem; text-align: left; cursor: pointer; width: 100%;
}
.vshot:hover { border-color: var(--accent-line); color: var(--ink); }
.vshot img { width: 104px; flex: none; border-radius: 5px; display: block; }
.vshot b { display: block; font-weight: 620; color: var(--ink); }
.vsub { display: block; font-size: .78rem; color: var(--ink-3); margin-top: 1px; }
.vanswer { margin-top: 6px; }
.vanswer img { width: 100%; max-width: 420px; border: 1.5px solid var(--accent-line);
  border-radius: 9px; display: block; }

/* Full-screen photo. A cab is bright and the number is in small print, so the
   photo gets the whole viewport rather than a polite modal. */
#shotbox { position: fixed; inset: 0; z-index: 50; border: 0; padding: 0;
  margin: 0; width: 100%; height: 100%; max-width: none; max-height: none;
  background: rgba(12,14,10,.94); }
#shotbox::backdrop { background: rgba(12,14,10,.94); }
#shotbox .sb {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px; padding: 16px;
  overflow: auto;
}
#shotbox img { max-width: 100%; max-height: calc(100% - 108px);
  object-fit: contain; border-radius: 8px; cursor: zoom-in; }
/* A landscape photo in a portrait phone leaves the small print unreadable, and
   the small print is the whole reason for opening it. So it zooms: the frame
   scrolls and the picture goes past the edge of the screen. */
#shotbox.zoom .sb { align-items: flex-start; justify-content: flex-start; }
#shotbox.zoom img { max-width: none; max-height: none; width: 260%;
  cursor: zoom-out; }
#shotbox.zoom p { display: none; }
#shotbox .hint { color: #b2bba9; font-size: .8rem; margin: 0; }
#shotbox.zoom .hint { display: none; }
#shotbox p { margin: 0; max-width: 62ch; text-align: center; color: #e9ede4;
  font-size: .92rem; line-height: 1.5; }
#shotbox .close {
  position: absolute; top: 14px; right: 14px; font: inherit; font-weight: 620;
  cursor: pointer; padding: 9px 15px; border-radius: 8px; min-height: 44px;
  background: #e9ede4; color: #171b15; border: 0;
}
.srcline p { margin: 0 0 5px; } .srcline p:last-child { margin: 0; }

.note { border-left: 3px solid var(--line); background: var(--surface-2); padding: 12px 15px; border-radius: 0 9px 9px 0; }
.note.ok   { border-color: var(--ok);   background: var(--ok-soft); }
.note.care { border-color: var(--warn); background: var(--warn-soft); }
.note.stop { border-color: var(--stop); background: var(--stop-soft); }
.note ul { margin: 0; padding-left: 19px; }
.note li { margin-bottom: 6px; } .note li:last-child { margin-bottom: 0; }

/* The stick is prepared on a computer, before anyone walks out to the
   machine, so its panel sits above the first question -- not at the bottom
   of an answer, which is where you read it having already made the trip.
   It is one closed line until somebody wants it, and it goes away once an
   answer is on screen: by then you are at the display, and the answer is
   what should have the room. */
.prep { margin: 4px 0 26px; }
.prep details {
  border: 1px solid var(--line); border-radius: 10px; background: var(--surface);
  overflow: hidden;
}
.prep summary {
  cursor: pointer; list-style: none; padding: 13px 15px;
  display: flex; align-items: center; gap: 10px; font-size: .93rem;
  font-weight: 560; min-height: 46px; box-sizing: border-box;
}
.prep summary::-webkit-details-marker { display: none; }
.prep summary::before {
  content: "+"; font-family: var(--mono); font-weight: 700; color: var(--accent);
  width: 1em; text-align: center; flex: none;
}
.prep details[open] summary::before { content: "\2013"; }
.prep details[open] summary { border-bottom: 1px solid var(--line-soft); }
.prep summary:hover { color: var(--accent); }
.prep .inner { padding: 14px 15px 16px; }
.prep p { margin: 0 0 11px; font-size: .92rem; }
.prep p:last-child { margin: 0; }
.prep .skip { color: var(--ink-3); font-size: .87rem; }
.prep ol { margin: 0 0 12px; padding-left: 21px; font-size: .92rem; }
.prep ol li { margin-bottom: 8px; }
.prep ol li:last-child { margin-bottom: 0; }

.actions { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 24px; }
.btn {
  font: inherit; font-weight: 620; cursor: pointer; padding: 11px 18px;
  border-radius: 9px; border: 1.5px solid var(--line);
  background: var(--surface-2); color: var(--ink); min-height: 46px;
}
.btn:hover { border-color: var(--accent-line); }
.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.srcline { padding: 13px 20px; border-top: 1px solid var(--line); background: var(--surface-2); font-size: .76rem; color: var(--ink-3); }

footer { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line-soft); color: var(--ink-3); font-size: .82rem; }
footer p { margin: 0 0 10px; max-width: 64ch; }
footer .panel { background: none; border-color: var(--line-soft); }
footer .vbody { padding: 4px 16px 14px; }
footer .vbody p:last-child { margin: 0; }

/* ----------------------------------------------------------------- print */
@media print {
  .noprint, header, .q, .trail, footer { display: none !important; }
  body { background: #fff; color: #000; font-size: 11.5pt; }
  .wrap { max-width: none; padding: 0; }
  .card { border: none; box-shadow: none; }
  .chead { background: none; border-bottom: 2px solid #000; padding: 0 0 10pt; }
  .body { padding: 12pt 0 0; }
  .facts { background: none; } .facts > div { background: none; }
  ol.steps li::before { background: #000; color: #fff; }
  ol.steps li, .note, .facts { break-inside: avoid; }
  h4 { break-after: avoid; }
  .key { background: none; border: 1px solid #000; box-shadow: none; }
}
"""

JS = r"""
const $ = (s, r = document) => r.querySelector(s);
const el = (t, a = {}, ...kids) => {
  const n = document.createElement(t);
  for (const [k, v] of Object.entries(a)) {
    if (v == null || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false)
    n.append(c.nodeType ? c : document.createTextNode(String(c)));
  return n;
};

/* A step names buttons in «guillemets»; each becomes a key cap. Split rather
   than replace, so nothing in the source text is ever treated as markup.
   If the display has a picture of that button, it goes inside the cap: the
   operator is hunting for a glyph on the glass, and the word alone makes them
   read every icon on the page to find it. */
const keys = (text, monitorKey) => {
  const icons = D.screenIcons[monitorKey] || {};
  const parts = text.split(/«([^»]*)»/);
  const out = [];
  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 0) { if (parts[i]) out.push(parts[i]); continue; }
    const icon = icons[parts[i].toLowerCase()];
    const cap = el('b', { class: 'key' + (icon ? ' hasicon' : '') },
      icon ? el('img', { src: icon.src, alt: '', title: icon.code }) : null,
      parts[i]);
    /* Punctuation right after a cap must not wrap onto its own line. */
    const tail = (parts[i + 1] || '').match(/^[,.;:!?)]+/);
    if (tail) {
      parts[i + 1] = parts[i + 1].slice(tail[0].length);
      out.push(el('span', { class: 'nb' }, cap, tail[0]));
    } else {
      out.push(cap);
    }
  }
  return out;
};

const CONF_TONE = { verified: 'ok', file_verified: 'check', confirm_on_machine: 'check' };

/* ----------------------------------------------------- reading it aloud */
/* Somebody with both hands in a machine cannot scroll. The page reads the
   steps out, one at a time, highlighting the one it is on so a glance finds
   the place again.

   Two voices can do it, and the page prefers the better one. Recorded: every
   line was read ahead of time by a real TTS model and shipped as an MP3
   named after the line (tools/render_voice.py). Spoken: the phone's own
   speechSynthesis, which is free and always current and sounds like a phone
   -- and is missing outright on some Android builds, where the interface
   exists with no engine behind it.

   The recordings win when they are there, and they cover the case the
   browser voice cannot: a device with no speech engine can still play audio.
   When a clip is missing, or the page is opened as a single file with no
   folder beside it, playback falls back to the phone mid-procedure rather
   than stopping. */
const say = { steps: [], clips: [], at: -1, playing: false,
              everSpoke: false, recorded: false };
const player = new Audio();
const canSpeak = () =>
  'speechSynthesis' in window && typeof SpeechSynthesisUtterance === 'function';
/* Clips for the procedure on the screen. Partial coverage counts: a step
   without a recording is spoken by the phone, which beats skipping it. */
const haveClips = () => !!(D.voice && D.voice.dir && say.clips.some(Boolean));
const canRead = () => canSpeak() || haveClips();
const clipUrl = id => D.voice.dir + id + D.voice.ext;

/* « » marks a button name for the eye. Spoken, the marks are noise, and a
   folder path reads better with its separators named than spelled. */
const forSpeech = text => text
  .replace(/«|»/g, '')
  .replace(/\\/g, ', ')
  .replace(/\s+/g, ' ')
  .trim();

function sayStop() {
  say.playing = false;
  say.at = -1;
  if (canSpeak()) speechSynthesis.cancel();
  player.pause();
  player.onended = player.onerror = null;
  document.querySelectorAll('ol.steps li.saying')
    .forEach(li => li.classList.remove('saying'));
  const b = $('#saytoggle');
  if (b) b.replaceChildren(icon('play'), 'Read the steps aloud');
}

function icon(kind) {
  const paths = {
    play: 'M8 5v14l11-7z',
    pause: 'M6 5h4v14H6zm8 0h4v14h-4z',
    stop: 'M6 6h12v12H6z',
  };
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', paths[kind]);
  svg.append(path);
  return svg;
}

function sayFrom(index) {
  if (!canRead() || index >= say.steps.length) { sayStop(); return; }
  say.at = index;
  say.playing = true;
  const items = document.querySelectorAll('ol.steps li');
  items.forEach(li => li.classList.remove('saying'));
  const here = items[index];
  if (here) {
    here.classList.add('saying');
    here.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  if (say.recorded && say.clips[index]) playClips(index);
  else speakStep(index);
}

/* The number and the step are two files -- see voice.py for why -- played
   back to back. The small gap between them lands where a pause belongs
   anyway, after "Step 4." */
function playClips(index) {
  const queue = [(D.voiceNums || [])[index], say.clips[index]]
    .filter(Boolean).map(clipUrl);
  let at = 0;
  const next = () => {
    if (!say.playing) return;
    if (at >= queue.length) {
      prefetch(index + 1);
      sayFrom(index + 1);
      return;
    }
    player.src = queue[at++];
    player.onended = next;
    /* A clip that will not load must not end the reading. Hand the rest of
       the procedure to the phone and carry on from the same step. */
    player.onerror = () => { say.recorded = false; speakStep(index); };
    player.play().catch(() => { say.recorded = false; speakStep(index); });
  };
  next();
}

/* Ask the browser for the next step's audio while the current one plays, so
   the gap between steps is not a download. */
function prefetch(index) {
  const id = say.clips[index];
  if (!id) return;
  const a = new Audio();
  a.preload = 'auto';
  a.src = clipUrl(id);
}

/* Replace the controls with a sentence saying why nothing is being read.
   Better than a button that appears to do nothing. */
function sayNote(text) {
  sayStop();
  const bar = $('.saybar');
  if (bar) bar.replaceChildren(el('p', { class: 'saynote' }, text));
}

function speakStep(index) {
  if (!canSpeak()) {
    sayNote('The recordings could not be loaded and this device has no '
      + 'speech voice of its own, so the steps cannot be read out. '
      + 'Everything else on the page still works.');
    return;
  }
  const line = new SpeechSynthesisUtterance(
    `Step ${index + 1}. ${forSpeech(say.steps[index])}`);
  line.lang = 'en';
  /* Slower than conversation: these are numbers and folder names being
     followed by hand, not prose being skimmed. */
  line.rate = 0.92;
  line.onstart = () => { say.everSpoke = true; };
  line.onend = () => { if (say.playing) sayFrom(index + 1); };
  /* Having the API is not having a voice: some devices ship the interface and
     no engine behind it, and speak() then fails silently. Rather than leave a
     button that appears to do nothing, say what happened -- once, and only
     after it has actually failed, since guessing up front would hide the
     feature from devices that can do it. */
  line.onerror = () => {
    if (!say.everSpoke) {
      sayNote('This device has no speech voice installed, so the steps '
        + 'cannot be read out. Everything else on the page still works.');
    } else {
      sayStop();
    }
  };
  speechSynthesis.speak(line);
}

function sayToggle() {
  if (!say.playing) {
    const paused = say.at >= 0
      && (say.recorded ? player.paused && player.src
                       : canSpeak() && speechSynthesis.paused);
    if (paused) {
      say.playing = true;
      if (say.recorded) player.play().catch(() => sayFrom(say.at));
      else speechSynthesis.resume();
    } else {
      sayFrom(say.at >= 0 ? say.at : 0);
    }
    $('#saytoggle').replaceChildren(icon('pause'), 'Pause');
  } else {
    say.playing = false;
    if (say.recorded) player.pause();
    else if (canSpeak()) speechSynthesis.pause();
    $('#saytoggle').replaceChildren(icon('play'), 'Continue');
  }
}

const S = { equip: null, mon: null, ver: null, job: null, route: null };
const monByKey = Object.fromEntries(D.monitors.map(m => [m.key, m]));

/* Which jobs and routes are actually documented for a display, so the wizard
   never offers a choice that leads to an empty page. */
const forMonitor = k => D.procedures.filter(p => p.m === k);
const versionOk = (p, v) => p.v.includes('*') || !v || p.v.includes(v);
/* Filtered by the machine as well as the display: the same box is bolted to a
   combine and to a sprayer, and a combine applies nothing, so offering it a
   prescription is offering a job that cannot happen. `outOfScope` is the
   separate list of jobs this project chose not to cover -- same effect on the
   menu, different reason, and the two stay apart in the source. */
const jobsFor = (k, v, equip) => D.objectiveOrder.filter(o =>
  !(equip && (D.objectives[o].notFor || []).includes(equip))
  && !(equip && (D.outOfScope[equip] || []).includes(o))
  && forMonitor(k).some(p => p.o === o && versionOk(p, v)));
/* Where one display makes a job specific, name it that way. */
const jobLabel = (o, k) => D.objectiveLabels[k + '|' + o] || D.objectives[o].label;
const routesFor = (k, v, o) => ['usb', 'cloud', 'desktop', 'manual'].filter(t =>
  forMonitor(k).some(p => p.o === o && p.t === t && versionOk(p, v)));

function resolve(k, v, o, t) {
  const c = forMonitor(k).filter(p => p.o === o && p.t === t);
  const exact = c.find(p => v && p.v.includes(v) && !p.v.includes('*'));
  if (exact) return { p: exact, exact: true };
  const generic = c.find(p => p.v.includes('*'));
  if (generic) {
    const specific = c.filter(p => !p.v.includes('*'));
    return { p: generic, exact: !specific.length,
      msg: specific.length ? 'These are the general steps for this display. Separate instructions exist for other monitor versions — go back and pick yours if it is listed.' : '' };
  }
  if (c.length) return { p: c[0], exact: false,
    msg: 'No steps are recorded for the version you picked. These were written for another release of the same display, so treat the menu names as a guide.' };
  return null;
}

/* ------------------------------------------------------------- rendering */
/* A question disappears once it is answered, so the screen shows the steps
   rather than the wizard that produced them. The breadcrumb above is the way
   back to any answer. */
const ORDER = ['equip', 'mon', 'ver', 'job', 'route'];

function reset(from) {
  ORDER.slice(ORDER.indexOf(from)).forEach(k => S[k] = null);
  render();
}

const answered = k => S[k] !== null;

function render() {
  sayStop();
  document.body.classList.toggle('go', answered('equip'));
  drawTrail();
  drawEquip();
  drawMonitors();
  drawVersions();
  drawJobs();
  drawRoutes();
  /* After drawRoutes, not before: that is what decides whether an answer is
     on screen, and the stick panel hides itself once one is. */
  drawPrep();
}

/* Preparing the stick is the one job that happens somewhere else: on a
   computer, before the trip out to the machine. Read at the bottom of an
   answer it is too late to act on, so it sits above the first question --
   closed, because plenty of jobs need no stick at all, and the panel has to
   be as easy to walk past as it is to open.

   Before a display is picked it says what to do and admits it cannot yet say
   the size limit or the folder. Once one is picked, the steps come from that
   display's own prepare_media procedure rather than from a second copy of
   the same knowledge written into the page -- the rules genuinely differ
   (a 2630 will not read a stick over 32 GB; a Gen 4 has no such limit and
   will not read NTFS), and a hand-written summary here would be the copy
   that goes stale. */
function drawPrep() {
  const host = $('#prepbody');
  const panel = $('#prep');
  /* Once an answer is on screen you are standing at the display, and this is
     no longer something you can act on. Give the room to the answer. */
  panel.hidden = !!$('#result') && !$('#result').hidden;
  if (panel.hidden) return;
  host.replaceChildren();

  const prep = S.mon && D.procedures.find(
    p => p.m === S.mon && p.o === 'prepare_media');

  host.append(el('p', {},
    'A stick the display will not read is the commonest reason nothing '
    + 'appears in the cab, and it is fixed on a computer, not out there. '
    + 'Do this before you go.'));

  if (prep) {
    host.append(el('ol', {}, prep.steps.map(s => el('li', {}, keys(s, S.mon)))));
    if (prep.care && prep.care.length) {
      host.append(el('p', { class: 'skip' }, prep.care[0]));
    }
  } else {
    host.append(el('p', { class: 'skip' },
      'The size limit and the file system differ between displays. Pick '
      + 'yours below and the exact rule for it appears here.'));
  }
  host.append(el('p', { class: 'skip' },
    'Not using a stick — typing the numbers in by hand, or the display sends '
    + 'its own data — then none of this applies. Carry straight on.'));
}

/* Undo the last answer given. Backing out of an answer whose route was chosen
   for it -- because only one was documented -- has to clear the job as well,
   or drawRoutes would helpfully pick that route again and nothing would move. */
function back() {
  const answeredKeys = ORDER.filter(answered);
  if (!answeredKeys.length) return;
  const last = answeredKeys[answeredKeys.length - 1];
  if (last === 'route' && routesFor(S.mon, S.ver, S.job).length <= 1) {
    reset('job');
  } else {
    reset(last);
  }
  scrollTo({ top: 0, behavior: 'smooth' });
}

function drawTrail() {
  const t = $('#trail'); t.replaceChildren();
  const crumbs = [];
  if (S.equip) crumbs.push(D.equipment[S.equip]);
  if (S.mon) crumbs.push(monByKey[S.mon].model);
  if (answered('ver') && S.mon) {
    const v = monByKey[S.mon].versions.find(x => x.key === S.ver);
    crumbs.push(v ? v.label : 'Any version');
  }
  if (S.job) crumbs.push(jobLabel(S.job, S.mon));
  if (answered('route') && routesFor(S.mon, S.ver, S.job).length > 1)
    crumbs.push(D.transports[S.route].label);
  if (!crumbs.length) return;

  const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  arrow.setAttribute('viewBox', '0 0 24 24');
  arrow.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M15.4 4.6 8 12l7.4 7.4 1.4-1.4L10.8 12l6-6z');
  arrow.append(path);

  const more = el('span', { class: 'dot', hidden: true, 'aria-hidden': 'true' }, '…');
  const spans = crumbs.map((c, i) =>
    el('span', { class: i === crumbs.length - 1 ? 'now' : '' }, c));
  const dots = spans.map(() => el('span', { class: 'dot', 'aria-hidden': 'true' }, '·'));
  const box = el('div', { class: 'crumbs' }, more);
  spans.forEach((s, i) => {
    box.append(s);
    if (i < spans.length - 1) box.append(dots[i]);
  });

  t.append(
    el('button', { class: 'backbtn', type: 'button', onclick: back },
      arrow, 'Back'),
    box);
  fitCrumbs(box, spans, dots, more);
}

/* Drop leading crumbs, whole, until the line fits -- the last one always
   stays, because "where you are" is the part the trail exists to say. Runs
   after the row is in the document: it is a measurement, not a guess.

   Measured against what the crumbs would like to be, not what they currently
   are. The last one is allowed to shrink, so the row never reports an
   overflow -- it just squeezes that crumb down to "Pull ..." while three
   crumbs nobody needed keep their full width. scrollWidth on a clipped span
   still gives the width of the text inside it. */
function fitCrumbs(box, spans, dots, more) {
  const GAP = 7;
  const wanted = () => {
    let w = -GAP;
    for (const c of box.children) if (!c.hidden)
      w += GAP + Math.max(c.scrollWidth, Math.ceil(c.getBoundingClientRect().width));
    return w;
  };
  for (let i = 0; i < spans.length - 1; i++) {
    if (wanted() <= box.clientWidth) return;
    spans[i].hidden = true;
    dots[i].hidden = true;
    more.hidden = false;
  }
}

const show = (id, on) => { $(id).hidden = !on; };
const step = () => { render(); requestAnimationFrame(() =>
  scrollTo({ top: 0, behavior: 'smooth' })); };

function drawEquip() {
  show('#q1', !answered('equip'));
  if (answered('equip')) return;
  const host = $('#equip'); host.replaceChildren();
  const counts = {};
  D.monitors.forEach(m => m.equipment.forEach(e => counts[e] = (counts[e] || 0) + 1));
  Object.entries(D.equipment).filter(([k]) => counts[k]).forEach(([k, label]) => {
    host.append(el('button', {
      class: 'chip',
      onclick: () => { S.equip = k; step(); },
    }, el('span', {}, label), el('span', { class: 'n' }, counts[k] + ' displays')));
  });
}

function drawMonitors() {
  show('#q2', answered('equip') && !answered('mon'));
  if (!answered('equip') || answered('mon')) return;
  const host = $('#mons'); host.replaceChildren();
  D.monitors.filter(m => m.equipment.includes(S.equip)).forEach(m => {
    host.append(el('button', {
      class: 'mcard', onclick: () => pickMonitor(m.key),
    },
      el('span', { class: 'b' }, m.brand),
      el('span', { class: 'm' }, m.model),
      el('img', { src: D.icons[m.icon], alt: '' })));
  });
}

function pickMonitor(key) {
  S.mon = key; S.ver = S.job = S.route = null;
  if (!answered('equip')) S.equip = monByKey[key].equipment[0] || null;
  step();
}

/* Open a photograph of the real screen. The number people are hunting for is
   in small print at the bottom of a busy page, so it gets the whole viewport
   rather than a thumbnail. */
function openShot(src, caption) {
  $('#shotimg').src = src;
  $('#shotcap').textContent = caption || '';
  $('#shotbox').classList.remove('zoom');
  $('#shotbox').showModal();
}

$('#shotimg').addEventListener('click', () => {
  const box = $('#shotbox');
  box.classList.toggle('zoom');
  if (box.classList.contains('zoom')) $('.sb', box).scrollTop = 0;
});

function drawVersionHelp() {
  const host = $('#vhelp'); host.replaceChildren();
  const help = D.versionHelp[S.mon];
  if (!help) return;

  const body = el('div', { class: 'vbody' });
  body.append(el('p', { class: 'qnote' },
    'Look for the ', el('b', { class: 'key' }, help.field),
    ' line — it reads like ', el('b', { class: 'key' }, help.example), '.'));

  const list = el('ol', { class: 'vsteps' });
  help.steps.forEach((s, i) => {
    const last = i === help.steps.length - 1;
    const item = el('li', {}, keys(s.text, S.mon));
    if (s.button) {
      item.append(el('div', { class: last ? 'vanswer' : '' },
        el('img', { class: last ? '' : 'vbtn', src: s.button, alt: '' })));
    }
    if (s.screen) {
      item.append(el('button', {
        class: 'vshot', type: 'button',
        onclick: () => openShot(s.screen, s.lookFor),
      }, el('img', { src: s.screen, alt: '' }),
         el('span', {},
           el('b', {}, s.screenName || 'This screen'),
           el('span', { class: 'vsub' }, 'Tap to see it on a real machine'))));
    }
    list.append(item);
  });
  body.append(list);

  const extras = el('div', { class: 'more' });
  const shelf = (title, items, cls) => {
    if (!items.length) return;
    extras.append(el('details', {},
      el('summary', {}, el('span', { class: 'dot ' + (cls || '') }), title,
        el('span', { class: 'n' }, items.length)),
      el('div', { class: 'inner' },
        el('ul', {}, items.map(x => el('li', {}, x))))));
  };
  shelf('Which option do I pick?', help.readsAs ? [help.readsAs] : [], 'care');
  shelf('Worth writing down while you are there', help.alsoShows, '');
  shelf('Where this comes from', [help.evidence], '');
  if (extras.children.length) body.append(extras);

  host.append(el('details', { class: 'panel' },
    el('summary', {}, 'Find your monitor version here'),
    body));
}

function drawVersions() {
  show('#q3', answered('mon') && !answered('ver'));
  if (!answered('mon') || answered('ver')) return;
  drawVersionHelp();
  const host = $('#vers'); host.replaceChildren();
  const pick = v => { S.ver = v; S.job = S.route = null; step(); };
  monByKey[S.mon].versions.forEach(v => {
    host.append(el('button', { class: 'chip', onclick: () => pick(v.key) },
      el('span', {}, v.label), v.notes ? el('span', { class: 'sub' }, v.notes) : null));
  });
  host.append(el('button', { class: 'chip', onclick: () => pick('') },
    el('span', {}, 'I am not sure'),
    el('span', { class: 'sub' }, 'You get the general steps')));
}

function drawJobs() {
  show('#q4', answered('ver') && !answered('job'));
  if (!answered('ver') || answered('job')) return;
  const host = $('#jobs'); host.replaceChildren();
  const keys = jobsFor(S.mon, S.ver, S.equip);
  Object.entries(D.directions).forEach(([dir, dirLabel]) => {
    const inDir = keys.filter(k => D.objectives[k].dir === dir);
    if (!inDir.length) return;
    const g = el('div', { class: 'jobgroup' }, el('h3', {}, dirLabel));
    inDir.forEach(k => g.append(el('button', {
      class: 'job', onclick: () => { S.job = k; S.route = null; step(); },
    }, el('b', {}, jobLabel(k, S.mon)),
       el('span', {}, D.objectives[k].desc))));
    host.append(g);
  });
}

function drawRoutes() {
  const routes = answered('job') ? routesFor(S.mon, S.ver, S.job) : [];
  /* One documented route is not a question. Skip straight to the answer. */
  if (routes.length === 1 && !answered('route')) S.route = routes[0];
  show('#q5', answered('job') && !answered('route'));
  if (answered('route')) { showResult(S.route); return; }
  show('#result', false);
  if (!answered('job')) return;
  const host = $('#routes'); host.replaceChildren();
  routes.forEach(t => host.append(el('button', {
    class: 'chip', onclick: () => { S.route = t; step(); },
  }, el('span', {}, D.transports[t].label),
     el('span', { class: 'sub' }, D.transports[t].desc))));
}

function showResult(t) {
  const r = resolve(S.mon, S.ver, S.job, t);
  const host = $('#result'); host.replaceChildren();
  if (!r) { host.hidden = true; return; }
  const p = r.p, m = monByKey[S.mon], obj = D.objectives[S.job];
  const ver = m.versions.find(v => v.key === S.ver);

  const card = el('div', { class: 'card' },
    el('div', { class: 'chead' },
      el('img', { src: D.icons[m.icon], alt: '' }),
      el('div', { class: 't' },
        el('h2', {}, jobLabel(S.job, S.mon)),
        el('p', {}, m.label + ' · ' + D.directions[obj.dir]),
        el('div', { class: 'tags' },
          el('span', { class: 'tag ' + CONF_TONE[p.conf],
                       title: D.confidence[p.conf].desc },
             D.confidence[p.conf].label),
          el('span', { class: 'tag' }, ver ? ver.label : 'Any version'),
          el('span', { class: 'tag' }, D.transports[p.t].label)))));

  const body = el('div', { class: 'body' });
  /* A version fallback changes what the steps are worth, so it stays on
     screen. The confidence wording is a qualifier and moves to the tag's
     tooltip and the reference stack below. */
  if (r.msg) body.append(el('div', { class: 'note care' }, r.msg));

  const facts = el('dl', { class: 'facts' });
  const fact = (k, v, code) => { if (!v || /^n\/a/i.test(v)) return;
    facts.append(el('div', {}, el('dt', {}, k),
      el('dd', {}, code ? el('code', {}, v) : v))); };
  fact('File format', p.fmt);
  if (p.ext.length) fact('File parts', p.ext.join('  '));
  fact('Exactly where it goes', p.path, true);
  fact('Format the stick as', p.fs);
  fact('Platform', p.plat);
  fact('Allow about', p.min + ' minutes');
  if (facts.children.length) { body.append(el('h4', {}, 'The file'), facts); }

  /* Collected, then rendered as one stack of openable rows after the steps. */
  const later = [];
  const block = (title, items, cls) => {
    if (!items || !items.length) return;
    later.push({ title, items, cls });
  };
  block('Before you start', p.pre, 'care');
  /* When somebody has photographed this exact job, the photos belong beside
     the steps they were taken at -- not in a gallery at the bottom, which
     nobody looks at while their hands are busy. */
  const walk = D.walkPhotos[[S.mon, S.job, p.t].join('|')];
  body.append(el('h4', {}, 'Step by step'));

  say.steps = p.steps;
  say.clips = p.say || [];
  say.everSpoke = false;
  say.recorded = haveClips();
  if (canRead()) {
    body.append(el('div', { class: 'saybar noprint' },
      el('button', { class: 'saybtn', id: 'saytoggle', type: 'button',
                     onclick: sayToggle }, icon('play'), 'Read the steps aloud'),
      el('button', { class: 'saybtn quiet', type: 'button', onclick: sayStop },
        icon('stop'), 'Stop')));
    body.append(el('p', { class: 'saynote noprint' },
      'Reads one step at a time and lights up the one it is on. '
      + 'Works with the phone in your pocket.'));
  }
  body.append(el('ol', { class: 'steps' }, p.steps.map((s, i) => {
    const item = el('li', {}, keys(s, S.mon));
    const shot = walk && walk.steps[i];
    if (shot && shot.button) {
      item.append(el('img', { class: 'vbtn', src: shot.button, alt: '' }));
    }
    if (shot && shot.screen) {
      item.append(el('button', {
        class: 'vshot noprint', type: 'button',
        onclick: () => openShot(shot.screen, shot.lookFor),
      }, el('img', { src: shot.screen, alt: '' }),
         el('span', {},
           el('b', {}, shot.screenName || 'This screen'),
           el('span', { class: 'vsub' }, 'Tap to see it on a real machine'))));
    }
    return item;
  })));
  if (walk) block('Where these photos were taken', [walk.evidence], 'ok');
  if (p.conf !== 'verified')
    block('How sure is this?', [D.confidence[p.conf].desc], 'care');
  block('Check it worked', p.ok, 'ok');
  block('Worth knowing', p.care, '');
  block('What usually goes wrong', p.bad, 'stop');

  const more = el('div', { class: 'more' });
  later.forEach(b => more.append(el('details', {},
    el('summary', {},
      el('span', { class: 'dot ' + b.cls }),
      b.title,
      el('span', { class: 'n' }, b.items.length)),
    el('div', { class: 'inner' },
      el('ul', {}, b.items.map(i => el('li', {}, keys(i, S.mon))))))));

  const sources = [];
  if (p.src.length) sources.push('Sources: ' + p.src.join(' · '));
  if (D.iconCredits[S.mon] && more.querySelector('.key img'))
    sources.push(D.iconCredits[S.mon]);
  /* Where the claim comes from belongs with the other reference material, not
     in a grey footer that reads as boilerplate and gets skipped. */
  if (sources.length) {
    more.append(el('details', {},
      el('summary', {}, el('span', { class: 'dot' }), 'Where this comes from'),
      el('div', { class: 'inner src' }, sources.map(x => el('p', {}, x)))));
  }
  if (more.children.length) body.append(more);

  body.append(el('div', { class: 'actions noprint' },
    el('button', { class: 'btn primary', onclick: printSteps }, 'Print this'),
    el('button', { class: 'btn', onclick: () => { reset('equip');
        scrollTo({ top: 0, behavior: 'smooth' }); } }, 'Start over')));

  card.append(body);
  host.append(card);
  host.hidden = false;
}

/* fitCrumbs measured the width it had at the time. Turning the phone sideways
   gives it a different one, so measure again. */
addEventListener('resize', drawTrail);

/* Paper has no disclosure triangles, and a printed page of collapsed rows
   would quietly drop the cautions and the failure modes -- the parts somebody
   pinned it to the wall for. Open everything for the print, then put back
   exactly what the reader had open. */
addEventListener('beforeprint', () => {
  document.querySelectorAll('details').forEach(d => {
    if (!d.open) { d.dataset.wasShut = '1'; d.open = true; }
  });
});
addEventListener('afterprint', () => {
  document.querySelectorAll('details[data-was-shut]').forEach(d => {
    d.open = false; delete d.dataset.wasShut;
  });
});

/* Printing can be blocked when the page is embedded. Say so plainly rather
   than leaving a button that quietly does nothing. */
function printSteps(e) {
  try { window.print(); }
  catch (err) {
    e.target.replaceChildren(document.createTextNode(
      'Use your browser’s own Print command'));
    e.target.disabled = true;
  }
}

/* -------------------------------------------------------------- search */
$('#find').addEventListener('input', e => {
  const q = e.target.value.trim().toLowerCase();
  const hits = $('#hits'); hits.replaceChildren();
  if (q.length < 2) return;
  D.monitors.filter(m =>
    (m.brand + ' ' + m.model + ' ' + m.aka.join(' ') + ' ' + m.generations)
      .toLowerCase().includes(q)
  ).slice(0, 6).forEach(m => hits.append(el('button', {
    onclick: () => { e.target.value = ''; hits.replaceChildren(); pickMonitor(m.key); },
  }, el('img', { src: D.icons[m.icon], alt: '' }),
     el('span', {}, m.brand + ' ' + m.model))));
});

/* Light unless somebody asks otherwise. localStorage is wrapped because an
   embedded page is not always allowed it, and losing the preference is a much
   smaller problem than the page failing to start. */
const THEME_KEY = 'ofpe-theme';
const readTheme = () => {
  try { return localStorage.getItem(THEME_KEY); } catch { return null; }
};
function setTheme(name) {
  document.documentElement.dataset.theme = name;
  $('#theme').textContent = name === 'dark' ? 'Light mode' : 'Dark mode';
  $('#theme').setAttribute('aria-label',
    name === 'dark' ? 'Switch to the light page' : 'Switch to the dark page');
  try { localStorage.setItem(THEME_KEY, name); } catch { /* not allowed here */ }
}
setTheme(readTheme() === 'dark' ? 'dark' : 'light');
$('#theme').addEventListener('click', () => setTheme(
  document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));

$('#shotbox').addEventListener('click', e => {
  if (e.target.id === 'shotbox') e.target.close();
});

render();
"""


def build() -> None:
    html = f"""<title>OFPE Monitor Guide</title>
<style>{CSS}</style>

<div class="wrap">

<header>
  <h1>Getting files in and out of the monitor</h1>
  <p class="tagline">The exact folder, and the exact buttons &mdash; for your
    machine.</p>
  <div class="rule"></div>
  <div class="search">
    <label class="sr-only" for="find" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Search for your display</label>
    <input id="find" type="search" autocomplete="off"
           placeholder="Know your display? Type it &mdash; 2630, Pro 700, GFX-750, CEMIS&hellip;">
    <div class="hits" id="hits"></div>
  </div>
</header>

<button class="themebtn noprint" id="theme" type="button"></button>

<div class="trail" id="trail"></div>

<section class="prep noprint" id="prep">
  <details>
    <summary>Using a USB stick? Set it up on the computer first</summary>
    <div class="inner" id="prepbody"></div>
  </details>
</section>

<section class="q" id="q1">
  <div class="qhead"><span class="qnum">01</span><h2 class="qtitle">What are you working with?</h2></div>
  <div class="chips" id="equip"></div>
</section>

<section class="q" id="q2" hidden>
  <div class="qhead"><span class="qnum">02</span><h2 class="qtitle">Which display is in the cab?</h2></div>
  <div class="grid" id="mons"></div>
</section>

<section class="q" id="q3" hidden>
  <div class="qhead"><span class="qnum">03</span><h2 class="qtitle">Which monitor version?</h2></div>
  <p class="qnote">Menus move between releases. Not sure? Pick the last option.</p>
  <div id="vhelp"></div>
  <div class="chips" id="vers"></div>
</section>

<section class="q" id="q4" hidden>
  <div class="qhead"><span class="qnum">04</span><h2 class="qtitle">What do you want to do?</h2></div>
  <div class="jobs" id="jobs"></div>
</section>

<section class="q" id="q5" hidden>
  <div class="qhead"><span class="qnum">05</span><h2 class="qtitle">How does the data travel?</h2></div>
  <div class="chips" id="routes"></div>
</section>

<div class="result" id="result" hidden></div>

<dialog id="shotbox">
  <div class="sb">
    <button class="close" type="button" onclick="shotbox.close()">Close</button>
    <img id="shotimg" alt="">
    <p id="shotcap"></p>
    <p class="hint">Tap the photo to zoom in</p>
  </div>
</dialog>

<footer>
  <details class="panel">
    <summary>How to read these answers</summary>
    <div class="vbody">
      <p>Folder paths and file formats are checked against manufacturer
        documentation. Exact menu names move between monitor versions, which is
        why each answer says whether it is verified or worth confirming on the
        machine.</p>
      <p>Two kinds of picture appear here, and they are not the same kind of
        thing. The drawing of each display is our own schematic of its shape
        &mdash; not a photograph, and carrying no manufacturer logo or mark. The
        small icons inside a step are different: they are the actual application
        icons from the display, reproduced from the manufacturer's operator
        manual, because an icon only earns its place by matching the glyph on
        the glass. Each answer that shows one credits the manual it came
        from.</p>
    </div>
  </details>
</footer>

</div>

<script>const D = {json.dumps(DATA, separators=(",", ":"))};
{JS}</script>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024 / 1024:.2f} MB)")
    print("  (README quotes this count in a few places — keep them in step)")
    print(f"  {len(procedures)} procedures, {len(monitors)} displays, {len(icons)} icons")


if __name__ == "__main__":
    build()
