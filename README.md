# OFPE Field Data Platform

**How do I get this file into the monitor — and how do I get the data back out?**
That is the question this platform answers. Pick your equipment, your display and
your software version, say what you are trying to do, and get the exact file
format, the exact folder on the USB stick, and the buttons to press.

Generating guidance lines is the supporting act.

Three tabs:

- **Guide** — the procedure wizard. Public, no login, printable.
- **Download lines** — a producer picks a machine and downloads AB lines in the
  format that display reads.
- **Operations** — machine library, field import, line generation and fitting.

## Running it

**Windows** — double-click **`start.bat`**.
**macOS / Linux** — run **`./start.sh`**.

That is the whole thing. On the first run it builds a private Python
environment beside the script, installs what it needs, loads a demo machine and
field so there is something to look at, and opens your browser. Every run after
that just starts, in a couple of seconds. Nothing it installs can affect any
other Python on the machine; deleting the `.venv` folder undoes all of it.

Leave the black window open while you use the app; closing it stops the server.

You need Python 3.11 or newer. If it is missing, the launcher says so and links
the installer — the one thing to remember there is to tick **"Add python.exe to
PATH"** on the installer's first screen.

To check everything works, double-click **`run-tests.bat`** (or run
`.venv/bin/python -m pytest tests -q`). The suite runs against a temporary
in-memory database and never touches your data.

<details>
<summary>Running it by hand instead</summary>

```bash
pip install -r requirements.txt
python3 run.py                 # seeds on first run, then serves
python3 run.py --open          # ... and opens a browser
python3 run.py --no-seed       # start with an empty library
python3 run.py --port 8080     # if 8000 is taken
python3 run.py --host 0.0.0.0  # reachable from the office network
python3 run.py --seed          # reload the demo data and exit
```

Only if you change the terminal drawings:

```bash
pip install pillow
python3 tools/generate_icons.py
```

</details>

## What to try first

The **Guide** tab needs no data at all — the 264 procedures are built in. Pick
a combine, pick a Gen 4, pick the 2025-3 software version, ask to load guidance
lines, and read what comes back. Then change the version to OS 11.x and watch
the answer change, which is the whole point of the version step.

The demo data is there for the other two tabs: **Download lines** has three
machines with generated AB lines ready to export, and **Operations** shows the
coverage table and the corrections queue.

---

## The guide

Six questions, each narrowing the next:

```
equipment type → brand/display → software version → what you want to do → how it travels → the procedure
```

**264 procedures across 23 displays.** Every answer carries the file format, the
exact media path, the filesystem, numbered click-by-click steps, how to check it
worked, what usually goes wrong, and the source the claim came from. The result
card prints cleanly — that is the artefact you carry to the machine.

Three things fall out of having the whole matrix:

- **Every answer is a link.** The four coordinates live in the URL fragment, so
  a procedure is something you paste into a message. Opening the link lands
  straight on the card.
- **Every display has a handbook.** `/handbook?monitor_key=…&version=…` renders
  *every* procedure for one display as a single printable document — for
  training an operator, for the folder in the workshop, for a machine handover.
- **Every card suggests what is next.** The trip to the machine to load a
  prescription is also the moment to pull last week's work data off it.
- **Every card can be corrected.** A button sends back what the screen actually
  said. See below — this is the only honest route from "confirm the wording" to
  "verified".

### Why the version step exists

It is not decoration. The same display on a different release moves menus,
renames "Data Transfer" to "File Manager", and in one case *stops accepting a
file format it used to take* — from the 2025-3 update, a John Deere Gen 4 will
no longer import an Apex-era setup file directly. Someone following generic
instructions on that machine goes looking for a menu that is not there and
concludes their file is broken.

So a procedure applies to a **set** of releases, not one:

```python
version_key=("gen4_10x", "gen4_11x")   # same steps
version_key=("gen4_2025_3",)           # the rules changed
```

A set rather than a single key because software lines share behaviour in runs —
Case IH 28.x and 29.x take the same menu path and 30.x moved it. One entry per
release leaves holes, and a hole means the wizard silently stops offering a job
the machine can obviously do. `test_every_version_of_every_display_is_covered`
enforces that no such hole exists; it caught two real ones (Gen 4 on OS 11.x had
no guidance-import procedure at all) and one genuine product difference (CEMIS
FP1 has no direct shapefile import, so it needs its own ISOXML-based procedure).

The resolver never pretends. If it falls back to generic steps it says so, and
names which releases *do* have specific instructions.

### What you can ask for

| Direction | Jobs |
|---|---|
| **Into the monitor** | prescriptions, guidance lines, boundaries, client/farm/field setup |
| **Out of the monitor** | work data (yield / as-applied), guidance lines, boundaries, full backup |
| **On the monitor** | update the display software, prepare the USB stick |

Each is available by USB, by the manufacturer's cloud, or through their desktop
software — whichever routes actually exist for that display. The wizard only
offers combinations that resolve to a real procedure, and
`test_nothing_offered_by_the_api_leads_to_a_dead_end` walks the entire catalog
to keep that true.

### Cloud platforms

Fourteen covered, because "just use the cloud" is not advice until you say which
portal to log into:

John Deere Operations Center · AFS Connect · PLM Connect · Trimble Ag Software ·
AgFiniti · Raven Slingshot · Topcon Agriculture Platform · CLAAS TELEMATICS /
365FarmNet · Fendt Connect · Valtra Connect · MF Connect · IsoMatch FarmCentre ·
Panorama · agrirouter

Several brands run two platforms that do different jobs — CLAAS splits
telematics from agronomy — so the procedure names the right one rather than the
famous one.

### Corrections from the field

Folder paths and file formats are checked against manufacturer documentation.
Menu names are not checkable that way: they move between software releases, and
the only way anyone finds out is somebody standing in front of the screen. So
148 of the 264 procedures carry **Confirm the menu wording on the machine** —
that is an honest label, not a defect.

The button on every procedure card closes that loop. It asks four short
questions, only one of which is required, and files a correction that shows up
in the Operations tab as a queue. `worked_fine` is one of the options and needs
no text at all — a confirmation that the steps are right is as useful as a
complaint, and much rarer.

The form is deliberately short. A bad report beats no report, and a long form
gets abandoned in a cab.

### Icons

Every display has a schematic drawing generated by `tools/gerar_icones.py` —
screen proportion, physical keys, rotary encoder. They deliberately do not
reproduce photographs, logos or figurative marks; model names appear as text
only. Two variants are generated from one source: captioned for the spreadsheet,
caption-free for the web UI (where the model name is already real text beside the
picture).

---

## Read this first: there is no universal AB line file

This is the single most important thing about the problem, and the platform is
built around it rather than around wishing it away.

Roughly half the installed base runs a **closed** guidance format. John Deere
does not publish one. Trimble's `.agdata` container is AES-encrypted with a
cloud-held key. Ag Leader's `.agsetup` is undocumented. No third party can write
those files — not this platform, not anyone.

So every terminal in the catalog carries an honest verdict, and the producer sees
it *before* the download button, not after they have driven to the field:

| Level | What it means | Who |
|---|---|---|
| **Direct import** | Published open format, we write it in full. Copy to USB, import, drive. | Every ISOBUS terminal, via ISOXML |
| **Direct import (check wording)** | Standard format in a vendor-specific folder. File is right; menu names drift between firmware versions. | Case IH Pro 700, IntelliView IV, Precision Planting 20\|20, TeeJet |
| **Two steps, via desktop software** | Terminal format is closed. We write what the vendor's own software imports; that software writes the display file. | John Deere, Trimble, Ag Leader |
| **Best effort, unverified** | Folder layout known from the manual, payload bytes not yet confirmed against a real machine. Ships a shapefile fallback and says so. | Raven Viper 4, AgOpenGPS |
| **No file route** | Cloud API only. | (none currently) |

A "two steps" answer is not a failure. For John Deere it is genuinely the best
available path — and if the machine has JDLink, Operations Center pushes the line
over the air and the USB stick never comes out of the drawer.

**One real export promotes a row.** Every `Best effort, unverified` entry becomes
verified the moment you send a genuine file off a customer's display. That is the
highest-value thing you can do for this platform.

---

## Coverage

| Brand | Terminals | Format we write | Level |
|---|---|---|---|
| John Deere | GS3 2630, Gen 4 (4240/4600/4640), G5 | Shapefile + KML + GeoJSON → Operations Center | Two steps |
| Case IH | AFS Pro 700 | Shapefile "Multiswath" | Direct |
| Case IH | AFS Pro 1200 | ISOXML | Direct |
| New Holland | IntelliView IV | Shapefile "Multiswath" | Direct |
| New Holland | IntelliView 12 | ISOXML | Direct |
| Trimble | GFX-350/750/1060/1260, TMX-2050 | Shapefile → Trimble Ag Software | Two steps |
| Trimble | FmX, CFX-750, FM-1000 | Shapefile → Trimble Ag Software | Two steps |
| Ag Leader | InCommand 800/1200/Go, Integra | Shapefile → SMS | Two steps |
| Raven | Viper 4 / 4+ | `Raven/GFF/.../abLines` tree + shapefile | Unverified |
| CLAAS | CEMIS 1200, S10 | ISOXML | Direct |
| Fendt | FendtONE, Varioterminal | ISOXML + AGCO KML | Direct |
| Valtra | SmartTouch | ISOXML | Direct |
| Massey Ferguson | Datatronic 5, 9000-series | ISOXML | Direct |
| Topcon | X35, X25, XD, XD+ | ISOXML | Direct |
| Kverneland / Kubota | IsoMatch Tellus GO/PRO, K-Monitor | ISOXML | Direct |
| Müller-Elektronik | TOUCH 800/1200, TRACK-Leader | ISOXML + shapefile in `SHP/` | Direct |
| Precision Planting | 20\|20 Gen 1/2/3 | Shapefile in `SendTo2020/` | Direct |
| TeeJet | Matrix Pro 570GS/840GS, Aeros 9040 | Shapefile | Direct |
| AgOpenGPS | AgOpenGPS | Field folder text files + KML | Unverified |
| Generic | Any ISOBUS terminal (TC-BAS+) | ISOXML | Direct |
| Generic | QGIS / ArcGIS / FMIS | Shapefile, GeoJSON | Direct |

**ISOXML is the workhorse.** One exporter covers CLAAS, the whole AGCO family,
Topcon, Kverneland, Müller, current CNH, and anything else advertising TC-BAS.
That is why it got the most care.

Every download is a zip containing the format for that display, useful
alternatives, and a printable `HOW-TO-IMPORT.txt` with the exact folder path,
numbered steps, what this brand calls an AB line, and the mistakes that stop an
import working.

---

## Where lines come from

**1. Your own AB parameters.** Type or click A and B, or a point and a heading.
Also curves, pivots (centre + radius) and headland rings.

**2. The field boundary.** Ask the field which way to drive:

```
POST /api/lines/from-boundary  {field_id, machine_id, strategy, headland_passes}
```

`min_passes` scans every heading at half-degree steps and keeps the one needing
the fewest passes — fewest passes means fewest end-of-row turns, which is where
the time goes. Pass count is an integer so there are usually many ties; those are
broken by actually clipping the swaths and preferring the heading producing the
fewest *separate driven segments*. That matters: a concave boundary can slice one
pass into three, and each piece costs its own turn.

`longest_edge` aligns to the longest boundary edge — what most operators would
draw by hand, and on a rectangular field it agrees with `min_passes` anyway.

**3. Recorded machine data.** Upload last season's as-applied, yield or coverage
log and recover the line the machine actually drove:

- Derive a heading per point, then find the **dominant heading** by a
  length-weighted histogram modulo 180. Weighting by distance rather than point
  count stops short headland turns outvoting long productive passes.
- Split into passes, discarding discontinuities. *A straight hop from the end of
  one pass to the start of the next can be hundreds of metres long and point
  exactly along the dominant heading* — without gap detection it is mistaken for
  the longest pass in the job. (It was, until a test caught it.)
- Infer swath width from the spacing between passes. This is a
  greatest-common-divisor problem, not an average: an operator working back and
  forth leaves gaps of 12 m, 24 m and 36 m, and the mean of those is 24.
- Fit direction from all passes at once (averaging out GNSS drift), but **anchor
  the line on one real pass** — the longest. The reference is what every other
  swath is measured from, so it must sit on ground the machine actually covered.

Every fit returns a confidence, the measured spacing, and warnings. If the machine
is set up as 12 m but the passes are 11.4 m apart, it says so — that is 0.6 m of
deliberate overlap, and you should decide which number you want.

**4. Another brand's file.** Import ISOXML, shapefile, KML or GeoJSON and
re-export to anything else. This is the cross-brand translator.

---

## How it fits together

```
ofpe/web/       FastAPI, the no-build browser client, and the handbook renderer
db              SQLite
procedures/     _core.py  types, registry, resolver
                families.py  shapes shared by whole families of displays
                brands/   the knowledge, one module per manufacturer family
catalog         every brand, terminal, format, folder path, and how sure we are
readers         someone else's file  ->  our objects
writers         our objects          ->  someone else's file
generate        authoring and expanding guidance patterns
fitting         recovering a line from a track already driven
models          the canonical objects everything speaks
geo             projection and geodesy
```

`procedures/` is split so a brand module reads as pure knowledge — what the menu
says, where the folder is — with no machinery in the way. Twenty-odd ISOBUS
terminals genuinely behave identically, so that behaviour is written once in
`families.py`; writing it out twenty times would be twenty chances to introduce
a difference that is not real. Rebadged displays (the G5 and the Gen 4, the
IntelliView IV and the AFS Pro 700) are copied with `_mirror` rather than
aliased, so that when one eventually diverges the fix is editing one entry.

Readers and writers only ever talk to `models`, so adding a brand means adding one
writer and one catalog entry — nothing else changes.

### Two decisions worth knowing about

**Each field gets its own local transverse Mercator projection.** Not UTM: a field
near a zone edge would straddle two zones, and the scale factor at a zone edge is
about a metre per kilometre. Re-centring on the field puts it on the central
meridian, where scale error is ~1.5 mm/km. Headings leaving the system are
converted back to *true* azimuth, because grid north is not true north away from
the central meridian.

**Shapefile is read and written directly, not via GDAL.** It is a documented binary
layout and a few hundred lines of `struct`; carrying GDAL would dominate the
install for no benefit. Shapefile sets are always emitted complete —
`.shp`/`.shx`/`.dbf`/`.prj`/`.cpg` — because a lone `.shp` is the single most
common reason an import shows an empty list.

---

## API

| | |
|---|---|
| `GET /api/health` | counts |
| `GET /api/catalog/monitors` | every terminal, format and support level |
| `GET POST DELETE /api/machines` | machine library |
| `GET POST DELETE /api/fields` | field library |
| `GET POST DELETE /api/lines` | lines |
| `POST /api/lines/from-boundary` | generate from field shape |
| `GET /api/fields/{id}/heading` | score a heading without saving |
| `GET /api/lines/{id}/preview` | expand into clipped swaths |
| `POST /api/lines/{id}/publish` | show or hide from producers |
| `POST /api/import` | read any supported file |
| `POST /api/fit` | fit a line to a machine track |
| `POST /api/download` | build the zip for one display |
| `GET /api/producer/catalog` | published lines, joined to monitor profiles |
| `GET /api/guide/start` | equipment types, brands, objectives, coverage |
| `GET /api/guide/monitors` | displays filtered by equipment type and brand |
| `GET /api/guide/monitors/{key}/objectives` | what this display on this release can do |
| `GET /api/guide/procedure` | the resolved procedure, plus how it matched |
| `GET /api/guide/search` | free-text jump — "2630", "Pro 700", "CEMIS" |
| `GET /api/guide/coverage` | what is documented and what is missing |
| `POST /api/guide/report` | file a correction from the machine |
| `GET /api/guide/reports` | the correction queue |
| `GET /handbook` | every procedure for one display, printable |

Interactive docs at `/docs`.

---

## Tests

```bash
python3 -m pytest tests/ -q      # 162 tests
```

The ones that earn their keep are the **coverage invariants** in
`test_procedures.py` — no version holes, no objective offered that fails to
resolve, every terminal documented, every USB procedure naming its folder path.
A wrong step in a procedure is a typo someone reports; a hole in the version
matrix is silent, because nothing looks broken.

After those: the round-trips (write ISOXML, read it back, assert the geometry
survived), the bundle-content tests (every shapefile set complete, no duplicate
payloads, instruction sheet lists what shipped), and the fitting tests, which
synthesise a track from a known line and assert the fitter recovers the
parameters it was given.

`test_formats.py::test_every_monitor_can_build_a_download` walks the entire
catalog, so a terminal profile naming a format no writer implements fails at
build time rather than when a producer clicks download.

---

## Known limits

- **ISOXML enum integers are one edit from certain.** Element and attribute
  letter codes (`PFDA`, `GGPA`, `GPNA`–`GPNO`, `LSGA`–`LSGF`, `PNTA`–`PNTK`) were
  verified against the AgGateway ADAPT reference implementation. The enumeration
  *values* — pattern type 1–5, point type 6/7/8/9, line string type 5 — are the
  ones used consistently across ADAPT, CNH's published plugin and the wider ISOBUS
  tooling, but ISO 11783-10 is paywalled and isobus.net was unreachable during
  development. They are constants at the top of `writers/isoxml.py` for exactly
  that reason: if a real terminal export disagrees, one edit fixes every export.
- **Raven `.ab` payload is unconfirmed.** The folder tree is from Raven's manual;
  the file contents are not. Ships a shapefile fallback.
- **AgOpenGPS text field order is unconfirmed.** The coordinate convention is
  known (metres east/north of the `Field.txt` origin); the order within each line
  has changed between versions. Ships `Field.kml`, which is unambiguous.
- **Coordinate swaps are only half-detectable.** A longitude past ±90 in the
  latitude slot is rejected. A swap where both values land inside ±90 — most of
  Europe, much of Brazil — is indistinguishable from a real position. The map
  preview is what catches those.
- **Coverage is now broad but not uniform.** All ten objectives are documented
  across the major displays; the thin spots are AgOpenGPS (a PC application, so
  several jobs do not apply) and the specialist consoles. The Operations tab
  shows the remaining gaps as a table — that table is the work queue. Nothing is
  invented to fill a gap: a combination with no procedure says so and lists what
  *is* documented for that display.
- **Menu wording is the weakest claim.** Folder paths and file formats are
  verified against cited sources. Exact menu names drift between releases, which
  is why 148 of 264 procedures are flagged "confirm on the machine" and every
  card shows that flag. The correction button is the fix, and it needs people to
  use it — the knowledge base cannot improve on this axis without field reports.
- **No cloud APIs yet.** John Deere Operations Center exposes a guidance-line
  endpoint that creates AB lines directly, and Trimble has an equivalent. Both
  need a developer account and customer OAuth consent. That is the next step and
  it would promote John Deere and Trimble from two steps to one.
- **Curve offsets have a geometric limit.** Offsetting a curve toward its centre
  of curvature past the radius collapses it; those passes simply run out. That is
  real geometry, not a bug, but it means a tight curve produces fewer passes on
  the inside than a naive count suggests.


---

## Where this came from

The procedure knowledge base started life as two tabs in an unrelated
spreadsheet — a CWSI irrigation tool that happened to also carry a monitor
file-transfer guide. That guide held 24 procedures, all tagged "all versions".

This is that idea taken seriously: 264 procedures, a real software-version
dimension, every claim sourced and confidence-flagged, and a correction loop so
the flags can come down. The two projects share nothing but that origin, and
this one owns its own icon generator and assets.
