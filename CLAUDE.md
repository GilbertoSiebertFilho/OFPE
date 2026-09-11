# OFPE — monitor file guide + guidance-line platform

**What it is.** A guide that tells a producer *how to get a file into their monitor
and how to get data back out*: machine → monitor → monitor version → job → route
(USB / cloud / typed on the display) → the exact folder, file format and buttons.
Generating AB lines is the supporting act. Built for the Olds College on-farm trials
(OFPE), but written for any producer. README.md is the architecture reference; this
file is the context and the standing decisions.

- **Producer link (the product):** https://gilbertosiebertfilho.github.io/OFPE/
- **Repo:** https://github.com/GilbertoSiebertFilho/OFPE (public; Pages needs it public)
- **Local clone:** `C:\Users\gsiebertfilho\GIT\OFPE_Platform` (this folder)
- **Artifact copy of the guide:** https://claude.ai/code/artifact/9b226488-c8b8-4986-8181-c64c23332435
  (from the cloud session, not updated since; the site is the link that matters)

## Two front ends, one knowledge base

- `tools/build_guide.py` → **`OFPE-Guide.html`**: the page GitHub Pages serves (1.5 MB;
  icons baked in, cab photos fetched from `assets/photos/` and `voice/` beside it).
  `--offline` writes `OFPE-Guide-offline.html`, the same page with every photo baked
  in, for a stick or an email — gitignored, built on demand. The producer-facing UI
  (checklist, USB panel, Back button, voice, photos, brand filter, per-answer link and
  Share, "Take this to the machine" card) lives **here**, not in `ofpe/web`.
- `run.py` → FastAPI app with three tabs: Guide (older UI), Download lines, Operations
  (machine library, field import, line generation and fitting). Internal use.
- Knowledge: `ofpe/procedures/` — `_core.py` (types, registry, resolver, scope rules),
  `families.py`, `brands/*.py`, `walkthroughs.py` (photographed procedures own their
  steps), `screens.py` (Gen 4 app icons), `checklist.py`, `voice.py`.

## Commands (Windows)

```
.venv\Scripts\python -m pytest tests -q          # 214 tests, must stay green
.venv\Scripts\python tools\build_guide.py        # rebuild OFPE-Guide.html (commit it)
.venv\Scripts\python tools\build_guide.py --offline   # the single-file copy
.venv\Scripts\python run.py --open               # server app on :8000
```

To see the page as a producer does, serve the repo root and open `/`:
`.venv\Scripts\python -m http.server 8010` (the `guide` entry in
`.claude/launch.json`). Opening the file directly is not the same test — the site
is served from a folder, and that is where the photo paths and the links resolve.

Always pass `encoding="utf-8"` to `read_text`/`write_text`/`open`: Windows defaults to
cp1252 and mangles the «» label markers. CI runs Ubuntu + Python 3.11; local is 3.14.

## Shipping

tests → `build_guide.py` → commit (including `OFPE-Guide.html`) → push `main`.

**Pages Source is "Deploy from a branch" (main, root), so what is committed *is* the
live site** — `index.html` (the doorway, which keeps the `#` of a shared link),
`OFPE-Guide.html`, `assets/photos/`, `voice/`. The **Publish the guide** workflow
also runs on every push: it re-runs the tests and would deploy if the Source were
switched to GitHub Actions. Forgetting to rebuild the page means pushing steps the
site never shows.
Voice: the **Record the spoken steps** workflow (manual dispatch, KittenTTS, voice
*Jasper*) is incremental — reword a step, run it, only new lines are recorded.
Ask before committing or pushing; a push is live for producers within minutes.

## Standing product decisions (from the user, Aug–Sep 2026)

- App text is **English**; talk to the user in Portuguese. Keep it separate from CWSI.
- First question offers only **Tractor, Combine harvester, Seeder / air drill, Sprayer**
  (the catalog keeps all eight types; Precision Planting 20|20 is reachable by search).
- Brand is a **filter row** in question 2 ("All makes" default), not a separate question.
- "Which **monitor** version?" (not "software"); "Find your monitor version here".
- Jobs removed everywhere (`SCOPE_EXCLUSIONS`): Load specific point, Pull off marked
  points, Update the display software, Pull off guidance lines ("the monitor exports
  everything"). Combines never get prescriptions (physics, `Objective.not_for`).
- **Tractor menu is an allowlist**: Load AB lines, Load field boundaries, Pull off work
  data, Prepare the USB stick — on every monitor, the 2630 included.
- Label is **"Load AB lines"**. The typed route names the four numbers (Lat A, Long A,
  Lat B, Long B) and says it needs no USB stick.
- USB stick: **"32 GB or less — 4 GB is plenty"**, FAT32, empty before it goes in; the
  2630 pops a Data Transfer screen on plug-in; Gen 4 has no size cap but refuses NTFS.
  The USB preparation panel sits *before* "What are you working with?".
- Light theme by default, little visible text, details behind click-to-open, a
  **Back** button (no deletable chips), large type on phones.
- Harvest-day checklist on the first screen; **no numbers in checklist items** (a test
  enforces it — numbers come from the grower's trial sheet).
- Evidence tiers are enforced in code: `VERIFIED` / `FILE_VERIFIED` /
  `CONFIRM_ON_MACHINE`. Only the user's own cab photos promote a procedure to
  VERIFIED. Frames from third-party videos need credit; prefer the user's own photos.
  A rebadged twin inherits the steps at `CONFIRM_ON_MACHINE`, never the photos.
- **Every answer is a link** (`#e=…&m=…&v=…&j=…&r=…`), with **Share** / **Copy the
  link** on the card: sending one answer is how a producer is actually reached.
  Steps must therefore read without their photos ("as in the photo" is banned by a
  test) and the page must stay small enough to open on field data.

## Evidence we have

- GreenStar 3 2630 photographed by the user: find version, pull off work data, AB line
  typed by lat/long, AB line by USB (`assets/photos/john_deere_gs3_2630`).
  "Load field boundaries" on the 2630 is still reconstructed, not photographed.
- New Holland IntelliView IV, photographed 11 Sep 2026 on a combine at Olds College
  (88 photos in the user's Drive; `tools/extract_iv4_photos.py` cuts the 60 used):
  AB line typed as lat/long, AB line from a stick as **ISOXML v3** (the file made in
  Ag Leader SMS with «Generic ISO11783 (v3) - Type 1»), and pulling off work data as
  ISOXML. The Case IH AFS Pro 700 carries the same steps at CONFIRM_ON_MACHINE.
  Answers confirmed by the user: press «Copy» at the Swath Datum Mismatch Warning;
  «Back» on the run screen reaches the main menu.
- Gen 4: 60-page manual (RE338096) → 22 app icons in `assets/icons/john_deere_gen4`;
  typed lat/long route from Deere's onscreen help, still CONFIRM_ON_MACHINE.
- `docs/research/monitor-and-format-research.md` — the August multi-agent format
  research (brand by brand, ISOXML deep dive, sources), brought over from LINEGUIDER.

## Backlog (updated 2026-09-11, after the IntelliView IV)

1. **Gen 4 walkthrough from cab photos/videos** (the user's next intended step). The
   videos were sent by Gmail and a YouTube link; the cloud session could not open them.
2. Photograph the 2630 "Load field boundaries" route, and a Case IH AFS Pro 700 doing
   the three jobs it currently borrows from the IntelliView IV.
3. Identify "RAVEN PRO" (probably Viper Pro) and "Topcon X20" from the producer survey
   before adding entries — a photo of each monitor settles it.
4. ISOXML device inventory reader (DVC/DET/DPD, 64-bit NAME decode, DDI list) and a
   `TLG*.BIN` parser — needs one real TASKDATA export from a trial machine.
5. The Download lines tab writes ISOXML v4 only. The IntelliView IV loaded **v3** from
   SMS, and the research doc says the whole Voyager generation wants v3 — so the v3
   flat dialect from LINEGUIDER is worth porting before anyone downloads a line for a
   Pro 700 or an IntelliView IV.
6. From LINEGUIDER, not yet in this app: lat/long "go to" box to find a field on the map
   (asked four times, 7–8 Aug, never delivered); satellite map with a Clients → Farms →
   Fields tree in Operations (here it is an SVG preview); ISOXML v3-flat and v2
   (Outback) dialects plus per-brand packaging quirks (Fendt `TASKDATA.zip`, CLAAS
   unzipped, Müller extended mode, Pro 700 ≥ 31.31 toggle); ft/m toggle.
7. Cloud APIs (John Deere Operations Center guidance lines) would turn Deere into one step.
8. Competitor check: NEXT Wayline Converter (AGCO/FarmFacts) overlaps the Download
   lines tab; the version-aware, cross-brand, photographed guide is the part nobody has.

## History

- 5–8 Aug: **LINEGUIDER** (`GIT\LINEGUIDER`, Node + React + MapLibre), the first
  build: operations map, producer download tab, 20 displays. Superseded; left in place.
- 11 Aug: the user's pivot — the point is getting files in and out of monitors, with
  the version step. Built in a cloud session on the CWSI repo, split into this repo.
- 11 Aug – 11 Sep: cloud session "Agriculture machine AB line platform": Pages site,
  2630 photos, Gen 4 icons, voice, checklist, machine and scope simplification,
  producer survey (Bourgault iCon and Outback Rebel added), brand filter.
- 11 Sep: consolidated into this local clone; the old chats were archived. Then the
  IntelliView IV from 88 cab photos, per-answer links with Share, photos moved out of
  the page, and the viewport/doctype fix that had the live site laid out 980 px wide
  on every phone since it went up.
