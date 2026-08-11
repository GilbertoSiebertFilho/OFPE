# AB Line Platform

Build agricultural guidance lines from field boundaries, recorded machine data or
hand-entered AB parameters — and hand them to producers in the file format their
display actually reads.

Two tabs, two audiences:

- **Operations** (you) — set up machines, import fields and monitor data, generate
  and preview lines.
- **Producer** (your customer) — pick a machine, tick the lines, download the file,
  follow the printed steps. No login.

```bash
pip install -r requirements.txt
python3 run.py --seed      # demo machine, field and lines
python3 run.py             # http://127.0.0.1:8000
```

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
web/        FastAPI + a no-build browser client
db          SQLite
catalog     every brand, terminal, format, folder path, and how sure we are
readers     someone else's file  ->  our objects
writers     our objects          ->  someone else's file
generate    authoring and expanding guidance patterns
fitting     recovering a line from a track already driven
models      the canonical objects everything speaks
geo         projection and geodesy
```

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

Interactive docs at `/docs`.

---

## Tests

```bash
python3 -m pytest tests/ -q      # 114 tests
```

The ones that earn their keep are the round-trips (write ISOXML, read it back,
assert the geometry survived), the bundle-content tests (every shapefile set
complete, no duplicate payloads, instruction sheet lists what shipped), and the
fitting tests, which synthesise a track from a known line and assert the fitter
recovers the parameters it was given.

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
- **No cloud APIs yet.** John Deere Operations Center exposes a guidance-line
  endpoint that creates AB lines directly, and Trimble has an equivalent. Both
  need a developer account and customer OAuth consent. That is the next step and
  it would promote John Deere and Trimble from two steps to one.
- **Curve offsets have a geometric limit.** Offsetting a curve toward its centre
  of curvature past the radius collapses it; those passes simply run out. That is
  real geometry, not a bug, but it means a tight curve produces fewer passes on
  the inside than a naive count suggests.
