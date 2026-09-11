# LINEGUIDER — Monitor & Guidance-Line Format Research (Master Reference)

> **Read this next to the guide, not instead of it.** It was written in August
> 2026 for LINEGUIDER, the prototype this platform replaced, and it is kept
> because the format work behind it is sound and sourced. Two things in it have
> since been overtaken by photographs of real cabs:
>
> - "John Deere accepts no file-based guidance import" is about files *we* can
>   write. A GS3 2630 does import guidance lines from a stick — from a profile
>   John Deere's own software wrote. Both statements are true at once.
> - The Voyager displays (AFS Pro 700, IntelliView IV) are described here as
>   wanting ISOXML v3; an IntelliView IV has now been photographed doing exactly
>   that, with a v3 file from Ag Leader SMS.
>
> Where this document and a photographed procedure disagree, the photograph wins.

**Compiled:** 2026-08-05
**Method:** Synthesis of 10 parallel research agents covering John Deere, Trimble/PTx, CNH, Ag Leader, Topcon/Raven/Outback/Hexagon, AGCO/Claas/Kverneland/Müller-Elektronik, ISOXML deep-dive, Shapefile guidance exchange, and line-derivation algorithms. Conflicting claims are retained and flagged inline with **⚠ Conflict** markers; unverified claims are flagged **UNCERTAIN**.
**Note:** The tenth research stream (ecosystem/competitor landscape) arrived truncated; Section 5 is synthesized from cross-mentions in the other nine streams and should be treated as a partial view pending a dedicated follow-up pass.

---

## 1. Executive Summary

LINEGUIDER's core bet — ingest machine/monitor data, derive guidance lines (AB, A+, curve, pivot), and export them in each display brand's native import format — is feasible, but the export landscape splits sharply into three tiers. **Tier 1 (open, documented):** ISO 11783-10 "ISOXML" TASKDATA is the only genuinely open, XSD-published guidance-line container, and it is the confirmed/best import path for Trimble Precision-IQ (GFX/TMX), CNH AFS Pro 1200 / IntelliView 12, Outback MAX (S3), Fendt FendtONE, Massey Ferguson, Valtra, CLAAS S10/CEMIS 1200, Kverneland/Kubota IsoMatch, Müller-Elektronik/CCI terminals, and (with caveats) Raven CRX and Topcon Horizon. Critically, guidance elements (GGP/GPN) exist **only in ISOXML v4** (2015); many fielded terminals still speak v3.3 or older, where AB lines can only travel as a flat `LSG type=5` line-string under the field element — a real Outback MAX export inspected during this research uses exactly that legacy v2.0 flat style. A robust exporter must therefore emit both dialects. **Tier 2 (documented but constrained):** John Deere's ecosystem rejects file-based guidance import entirely (its shapefile paths are polygon-only, for Rx and boundaries); the only programmatic route is the gated Operations Center Guidance Lines REST API, which currently creates **straight AB lines only**. Leica mojo3D is the pleasant outlier: it natively imports guidance waylines as plain KML or shapefiles. **Tier 3 (closed/proprietary):** John Deere's RCD/Gen4 USB containers, Ag Leader's `.agsetup`, Raven's `.ab`/GFF, Topcon's native line format, and CNH's legacy CN1 are all undocumented; writing them requires reverse-engineering, gated SDK access (CNH), or routing through commercial desktop software (SMS, Farm Works, AFS Software).

Two cross-cutting realities shape v1 scope. First, **curves and pivots are the weak point everywhere**: AGCO's own cross-brand Wayline Converter refuses to handle anything but straight AB lines and boundaries; Fendt owners report ISOXML curve import failing in practice; JD's public API cannot create curves; and no vendor documents a shapefile pivot representation. Straight AB and A+ lines are the only patterns that port reliably, so v1 should ship straight-line export as the default, decompose curves into dense polylines where targeted terminals tolerate it, and warn users otherwise. Second, coordinate portability is not field-overlay agreement — John Deere computes AB extension accounting for earth curvature while Trimble historically uses flat point-to-point math, so identical A/B coordinates can produce non-overlapping passes across brands; export should use each brand's native convention (two points + heading in WGS84, letting the display do propagation) rather than pretending one geometry fits all. On the ingest side, pass-level GPS is obtainable from JD Operations Center point shapefiles (heading/swath/timestamp per point), open ISOXML TLG binary time-logs, Ag Leader/SMS text exports, and Precision Planting `.2020` files via a free ADAPT plugin; deriving AB lines from those streams (pass segmentation → per-pass total-least-squares fit → circular-statistics heading consensus → swath inference from cross-pass spacing) is well supported by published algorithms and open libraries (Shapely/GEOS, Fields2Cover, ADAPT ISOv4Plugin, isoxml-js/-dotnet), and no open-source competitor currently ships the exact "coverage points → native-format AB line" pipeline — that niche is open.

---

## 2. Brand-by-Brand Reference

### 2.1 John Deere

**Displays:** GreenStar 2 (2600), GreenStar 3 (2630), Gen4 (4240/4640, 4200/4600-series CommandCenter), G5/G5Plus; cloud = Operations Center (developer.deere.com APIs).

**Guidance import formats:**
- **No shapefile path for guidance lines exists anywhere in the JD ecosystem.** JD's shapefile ingestion (Files API, website upload, USB `Rx` folder) is explicitly restricted to **Polygon/MultiPolygon in WGS84** — used for Rx prescriptions and boundaries only. Guidance lines are line/point geometry and are structurally rejected.
- **Operations Center Guidance Lines REST API** (developer.deere.com/dev-docs/guidance-lines): polymorphic JSON with four subtypes (AB Line, A+ Heading, AB Curve/Adaptive Curve, Circle Track/pivot). GET returns active lines; **POST currently supports creating ABLine only**. ABLine object: `@type:"ABLine"`, `aPoint`/`bPoint` (lat/lon), `heading` (degrees, North=0), `eastShift`/`northShift` (centimeters), `tramOffset`/`tramSpacing` (0–20), optional `shapes` array (MultiPoint per continuous track segment), and a `spatialProjection` object seen using JD-proprietary `"dtiProjectionDeere"`. Access requires JD Developer partner registration/OAuth — gated, not anonymous. (Field names reconstructed from search-indexed portal content; the portal itself blocks anonymous fetches — high confidence but not verbatim-verified.)
- **Manual web UI:** Setup → Land → Guidance → create line by clicking two points + heading. This documented click-flow is the zero-risk fallback LINEGUIDER can generate instructions for.
- **ISOXML on Gen4:** OS 18-2 (2018) added AEF TC-GEO ISOXML task import/export, but Deere's own release notes enumerate "client, farm, field, boundaries, products, prescriptions" — **guidance lines are conspicuously absent**. Assume GPN import is unsupported on Deere displays.

**USB folder layout:**
- **GS2 2600** — Compact Flash card, no zip: `RCD/` at card root containing `Setup.fds` (master index) + proprietary binaries. `Rx/` folder at root (same level as RCD) for prescription shapefiles (`.shp/.shx/.dbf` flat, no subfolders). One snippet-only source mentions a `GRX/` folder with `.fdShape` files — **UNCERTAIN**, unverified.
- **GS3 2630** — USB (FAT32, ≤32 GB recommended): `GS3_2630/ → <ProfileName>/ → RCD/`. Sibling display naming: `Command_Center/` (GS3 CommandCenter), `GS2_1800/` (GS2 1800). Operations Center "Setup File" zips extract to exactly `GS3_2630/`. Rx shapefile limits: 20-char zone/rate names, max 254 rates.
- **Gen4/G5** — File Manager app abstracts the USB (Import/Export/Delete/Operations Center tabs). Setup data lands in a `JD4600` folder, work data in `JD-Data`, Rx shapefiles in root `Rx`. **The internal schema of Gen4/G5 setup payloads (which carry Guidance Tracks) is undocumented — genuinely opaque.**
- Import conflict rule (Gen4/G5, verbatim from JD help): same name + same tracking method → USB copy silently replaces display copy; same name but different line → incoming renamed "Track1(1)".

**Farmer import steps (Rx/setup, documented):** GS3: insert USB after boot → auto "Data Transfer" dialog → Import Data (setup/guidance) or Import Shapefile Data (Rx). GS2: Rx folder loads automatically at power-up. Gen4/G5: Menu → File Manager → Import tab. Wireless: Data Sync (MTG modem/Wi-Fi + Basics license) auto-syncs boundaries, guidance tracks, products every ~30 s; G5 23-1 adds Data Sync Setup and Work Planner auto-attaching AutoPath plans.

**Monitor-data export formats (ingest side):** Operations Center exports agronomic point shapefiles (WGS84, ~1 Hz, per-point heading/distance/swath width/timestamp/yield/moisture; capped at 250 operations per export) and boundary shapefiles. `github.com/JohnDeere/SampleData` provides free sample datacards/shapefiles for parser development. Work data also flows via the gated Field Operations API.

**Third-party writability:** Effectively **none** for native containers — no public spec for RCD/`Setup.fds` or Gen4/G5 payloads; only commercial reverse-engineering exists (Trimble Farm Works reads GS2 `Setup.fds`; Farmplan Gatekeeper writes to a 2630 via an internal "2630 node" but declares Gen4 unsupported). JD release notes show active format churn (25.3 update dropped Apex/legacy setup-file import). No open-source parser exists (verified against GitHub). **Practical path: API for straight AB lines; generated manual-entry instructions for everything else.**

### 2.2 Trimble / PTx Trimble

**Displays:** Legacy "AgGPS" era — EZ-Guide 250/500, FmX/FmX Plus, CFX-750, AgGPS FMD. Modern "AgData"/Precision-IQ era — GFX-350, GFX-750 (legacy but format-compatible), GFX-1060, GFX-1260, TMX-2050. **⚠ Conflict:** the current ptxag.com TMX-2050 page says it runs "FmX+ firmware, not Precision-IQ," contradicting many official "Precision-IQ for TMX-2050" guides — likely shared hardware with different software images; verify per unit. "AgRemote" (from the project brief) could not be corroborated as a real Trimble product — likely a misremembered name.

**Guidance import formats:**
- **ISOXML TASKDATA is the explicitly documented third-party bridge** into Precision-IQ: place `TASKDATA.XML` on the USB, tap it in Data Transfer, and the display converts it to AgData in place.
- Trimble is the **one major brand whose native legacy guidance storage literally is an ESRI shapefile**: FmX/TMX-era displays keep one shapefile per field containing ALL of that field's lines as PolyLine records. Re-import **replaces** (does not merge) the field's lines. Community-documented injection trick (OptiSurface): rename a lines shapefile to `LineFeatures.SHP/.SHX/.DBF` and drop it into the field's folder — **UNCERTAIN** (unofficial; DBF schema undocumented).
- Precision-IQ Landmark Library: line landmarks with `Guidable=Yes` inside an imported field surface in the Patterns menu as guidance — an alternate import vector. Field cap: 1,000 feature lines.
- Legacy `.agf` (field) files are **encrypted**; the only public reverse-engineering (`Bullhill/agf-converter`, AGF→KML) confirms polygon decoding only; the cited AES key is **UNCERTAIN/unverified**.

**USB folder layout:**
- Legacy: root `AgGPS/`; prescriptions in `AgGPS\Prescriptions\` (`.shp/.shx/.dbf`, unzipped, FAT/FAT32); field data in `AgGPS\Data\<Grower>\<Farm>\<Field>\` (+`Task` subfolder) holding proprietary `.agf/.agt/.agi`.
- Precision-IQ: root `AgData/`; prescriptions `AgData\Prescriptions\`; vehicle profiles `AgData\Profiles\` (`.cfg`/`.vdb`). Conversions write `Output_AgGPS\AgData\`, `Output_ISOXML\AgData\`, `Output_AgData\` folders at USB root (auto-incrementing "(1)", "(2)"…).
- **⚠ Conflict:** multiple official manual revisions (2016–2023) instruct "make sure your USB has the AgGPS folder on the root" right beside the `AgData\Prescriptions\` path — unresolved whether dual-root support or a doc bug. **Defensive move: write into both `AgGPS\Prescriptions\` and `AgData\Prescriptions\`.**

**Farmer import steps (Precision-IQ, from official manuals):** Data Transfer icon → toggle "Show All USB Files" ON → tap the `AgGPS` folder or `TASKDATA.XML` on the USB → display converts it to a new `Output_*\AgData\` folder → navigate in, select items, tap Copy. Export mirror: select on Internal pane → Copy → "Copy As" popup (AgGPS or ISOXML) → lands in `Output_AgData`. Legacy CFX-750: Settings → Data → Manage Data → USB → Get/Send Data. Precision-IQ→legacy transfers require Farm Works desktop as decode bridge. Wireless: AutoSync (TMX-2050 fw 6.11+, GFX-750 fw 2.11+) syncs guidance lines/boundaries with Trimble Ag Software / FarmENGAGE.

**Monitor-data export:** Precision-IQ exports AgGPS or ISOXML from Data Transfer; FarmENGAGE cloud exports Guidance Lines & Boundaries to Shapefile **and KML** plus AgData/AgGPS/ISOXML/JD/CNH .cn1/Ag Leader formats — the industry's clearest documented KML guidance export (cloud level, not in-cab).

**Third-party writability:** Good. ISOXML→AgData conversion is Trimble-sanctioned. Trimble publishes official **ADAPT plugins** (AgGPS + AgData) built on its own File Transfer API (source location not public; register at PTx Ag Developer Network). WGS84 confirmed as required CRS for imported shapefiles.

### 2.3 CNH Industrial (Case IH / New Holland)

**Displays:** Legacy — AFS Pro 300/600/700, IntelliView IV (CN1 format, "until the Phoenix release" per CNH's own glossary). Current — AFS Pro 1200, IntelliView 12 (Android/"Phoenix", Trimble-derived guidance stack, **standard ISOXML**).

**Guidance import formats:**
- **Pro 700 / IntelliView IV:** native format is **CN1** — a *folder* with `.cn1` extension at USB root (observed contents: `Combine/`, `Shared/`, `Index.vy1`, `Log/`; internal `.TSA/.TSO/.VY1` files; likely "Voyager" lineage — UNCERTAIN). Two documented third-party inroads: (a) official **Shapefile Import** (doc CIH03291601): folder literally named `Shapefile` at USB root; supports prescriptions **and "Multiswath guidance lines"**; three power-cycle scenarios depending on `.cn1` presence; assignment via Data Management → **Import2** (Grower/Farm/Field/type/units). **⚠ Gap:** the Multiswath shapefile's `.dbf` attribute schema is undocumented anywhere — obtain a real AFS Software/SMS export and reverse it. (b) **ISOXML**: `TASKDATA` folder at USB root; display OFF on insert; auto-copies at boot; Data Management → Import2 → source ISOXML → type ALL. **Firmware switch:** ≤ SW 31.26 the Task Controller reads the TASKDATA folder directly; ≥ 31.31 it reads `.cn1` unless "ISOBUS data format" is enabled in TC settings. German OEM doc confirms the ISOXML export type list includes *Führungslinien* (guidance lines); the shapefile import path officially covers boundaries + Rx only per the same doc — **⚠ Conflict** with the Case IH Multiswath flyer; likely Multiswath rides a companion artifact from AFS desktop software rather than a raw hand-authored shapefile.
- **Pro 1200 / IntelliView 12:** standard **ISOXML v4** — `TASKDATA/TASKDATA.XML` at USB root, FAT32, power-cycle import. On-device UX for imported GPN patterns (auto-attach vs manual re-assignment) — **UNCERTAIN**, untested.

**Third-party writability:** CN1 is gated but real: CNH's Developer Portal offers a **CN1 SDK** (.NET Standard 2.0, read AND write, e.g. `ICNHV2SetupTaskColl`) and a **CN1 ADAPT Plugin** (supports AB, A+, curve, spiral, multi-point pivot patterns + boundaries) — both behind subscription keys and T&Cs, not on public GitHub. The ISOXML side is genuinely open: CNH enhanced the public **ADAPT ISOv4Plugin** (EPL-1.0) rather than closing it. Known CN1 writers: Ag Leader SMS, Case IH AFS Software / AFS Mapping and Records (Farm Works-derived; exports guidance to AFS Pro 300/700 and Trimble FM-750/FM-1000).

**Monitor-data export (ingest side):** Pro 700 writes finalized data to the `.cn1` on proper shutdown; zip the `.cn1` for cloud platforms (AFS Connect, FieldAlytics — note FieldAlytics wants the *parent* folder of the cn1 selected). Pro 1200 exports ISOXML; export lands in an `Export` folder on the stick.

### 2.4 Ag Leader

**Displays:** Compass (guidance-only), Versa, Integra (`.fw2`/`.ibk2` family); InCommand 800/1200 (`.fw3`/`.ibk3`); InCommand Go 10/16 (2024/25, presumed same family). Cloud = AgFiniti; desktop = SMS Basic/Advanced.

**Guidance import formats:** Everything guidance travels in **`.agsetup`** (setup/guidance/boundaries/markers; replaces legacy MSF/IBY/PAT/IRX/REF) — **proprietary and publicly undocumented; no open-source parser exists anywhere.** Logged data = **`.agdata`** (also carries guidance patterns). Individual patterns can be imported/exported via Manage Patterns → Import/Export. Legacy bridge: `.pat` (guidance) and `.iby` (boundary) still supported for Insight/Edge compatibility and are the only cross-generation bridge (Integra→InCommand). Shapefiles are accepted **only for prescriptions** (3-file set, any folder on the USB for Integra/InCommand; root-only on old Insight; operator manually picks rate column/units at import). ISOXML: displays have an "Enable ISO XML Export" setting — **export-only; no evidence of ISOXML guidance import** (UNCERTAIN/likely unsupported).

**USB folder layout:** exports auto-save into `USB:\<DisplaySerial>_<Nickname>\<dated>.agsetup` (exact separators unverified). Display file browser parses the container (expandable tree + boundary thumbnails) — implying a structured container (likely zip/SQLite/XML), unconfirmed.

**Farmer import steps:** insert USB → Home → External Storage / Data Transfer → Import Files → browse to `.agsetup` → confirm → per-item Conflict Resolution (Rename Import / Rename Existing / Merge; Merge unavailable for product mixes/configs). AgFiniti moves `.agsetup`/`.agdata` wirelessly, has in-cloud Guidance Line Management (import/view/reorder/export), and iPad-direct sync via the display's own hotspot.

**Guidance pattern types:** Straight AB (incl. A+ via typed heading), Adaptive Curve, Identical Curve, Pivot (driven or manual center), SmartPath (≤20 AB lines), Pattern Groups (≤20). Width up to 2000 ft.

**Third-party writability:** **None direct.** Realistic routes: (a) instruct farmers through SMS (which imports generic shapefiles but requires manual Guidance Layer creation — a raw AB-line shapefile does NOT auto-become guidance), (b) target the legacy `.pat` format that SMS emits (format undocumented publicly), or (c) manual on-display entry instructions. SMS itself is the industry's broadest format hub (exports PAT/GLN/FLD/Trimble/RDL guidance files; brand list includes JD, CNH, Trimble, Raven, AGCO et al.; SMS version must match display firmware — e.g. "SMS 24.0 required for InCommand 9.5 data").

### 2.5 Topcon

**Displays:** X14 (entry; shapefile yes, **no ISOXML**), X25/X30/X35/XD/XD+ — all run Horizon.

**Import formats:** Official 2016 spec sheet: X25/X30 have "Import/Export .shp" = yes, "Import/Export ISOXML" = yes, "ISO TaskData Compatible" = yes. **⚠ Conflict:** farmer reports (NewAgTalk) state "Boundary and AB lines are a proprietary format — you would need Topcon SGIS software," and "Rx files export out of SMS, but AB lines won't." Most likely resolution: ISOXML/shapefile paths reliably cover Rx/boundaries/tasks, but **GPN→usable AB line round-trip is unverified in practice** — empirical hardware testing required before relying on it. Topcon's native AB-line file format has no public extension or spec; AGCO's NEXT Wayline Converter lists Topcon among convertible wayline formats, proving it has been reverse-engineered by at least one third party. (Do not confuse with survey-side MAGNET `.tp3/.ln3` formats — unrelated product line.)

**USB layout / import steps:** Explorer-style browsing: `Clients > [Farmer] > [Farm] > [Field] > boundaries` (or `> VCR` for Rx). Correctly placed files auto-appear in Jobs. Horizon 5 added third-party boundary shapefile import. Cloud: Topcon Agriculture Platform (TAP) via Cloudlynk cellular/Wi-Fi dongles or USB.

**Third-party writability:** ISOXML in via TASKDATA convention (guidance fidelity UNCERTAIN); native format closed (SGIS-managed).

### 2.6 Raven

**Displays:** Viper 4/4+ (ROS), legacy Envizio Pro/Pro II, CR7/CR12 (CRX platform). Cloud = Slingshot.

**Import formats & USB layout:**
- Viper 4: guidance lines are native **`.ab` files** in a strict tree: `USB:\Raven\GFF\<Grower>\<Farm>\<Field>\abLines\*.ab` ("GFF" = Grower/Farm/Field). Import: File Manager → USB Manager → File Type "Guidance Lines" → browse **to the Grower folder level only** → select → Import. **Viper 4 cannot import third-party AB lines** — the .ab/GFF path is Raven-to-Raven only (forum + KB consensus). A Raven KB "Import ISO XML TASKDATA from SMS into the Viper 4" exists; confirmed to carry names/boundaries; **GPN guidance coverage UNCERTAIN**. Alternate container: Slingshot Archive `.ssa`.
- Envizio Pro: `\ePro\` root (`Global Data\Profiles\*.pfl`, `Work Orders\`, `Field Boundaries\` shapefile triplets); guidance file extension unconfirmed.
- CR7/CR12: named KB workflows exist for ISOXML import and boundary loading; CR12 adds "Operation Planning" (defines guidance/tram lines). Whether TASKDATA GPN patterns land as usable AB lines — **UNCERTAIN**.
- Boundaries only: shapefiles via `\Raven\...\Viper\misc\boundarySHP`.

**Note:** AgOpenGPS 6.8.0 ships a special "Raven ISOXML" export variant — implying Raven's ISOXML dialect has quirks (undocumented which).

**Third-party writability:** `.ab` internals undocumented (assume binary). Best available path: ISOXML TASKDATA for CRX-platform devices (test first); Slingshot `/JobData` API accepts zipped job data (internal layout unconfirmed).

### 2.7 Outback Guidance (Hexagon)

**Displays:** MAX & STX on "S3" software (eDriveXD/XC terminals); legacy STX pre-S3.

**Import formats (highest-confidence finding in this research — verified against a real device export):**
- Modern S3 firmware imports **ISOXML TASKDATA**: `/TASKDATA/` at USB root; insertion auto-prompts "Import?"; or Menu → Tasks → Import/Export → Import ISO-XML. **Caution:** exporting to a USB that already holds a TASKDATA overwrites it irreversibly.
- A real Outback MAX TASKDATA sample (AgJunction-generated, firmware 2.2.7.1.32180) was downloaded and inspected: it uses **ISOXML v2.0, multi-file layout** (`TASKDATA.XML` holding only `<XFR>` stubs; content in `PFD00000.xml`, `CTR00000.xml`, … each wrapped in `<XFC>`), and AB lines appear **without any GGP/GPN** — as `<LSG A="5" B="A=B 1"><PNT A="2" C="lat" D="lon" B="A"/><PNT ... B="B"/></LSG>` directly under `PFD`, multiple named lines per field. **This flat legacy style is the evidence-backed safe target for Outback.**
- Shapefile import is **polygon/boundary only** — "line files consisting of only two points will not be recognized." Shapefiles cannot deliver AB lines to Outback.
- Legacy STX (pre-S3, per the official 228-page manual): no shapefile/KML/ISOXML at all; guidance travels only inside proprietary job files — `S3Jobs/` folder at USB root with `.Log` (job log) and `.tem` (job template, which bundles boundaries + A=B lines + pivots + marks).

**Third-party writability:** Excellent for S3 firmware via legacy-flat ISOXML (verified format); none for pre-S3.

### 2.8 Hexagon / Leica mojo3D & mojoMINI

- **mojo3D:** the most open display researched. Imports AND exports waylines via USB in three formats: native "Mojo3D files" (extension unknown — UNCERTAIN), **Google Earth KML**, and **full shapefile set** (`.shp/.dbf/.prj/.shx`). Steps: Settings → Transfer Data → Import/Export to USB → "Guidance" (whole set) or Guidance → Wayline Management → per-line KML/Shapefile choice; naming conflicts auto-renamed or resolved manually. Exact USB folder placement not specified in the manual — test root vs named subfolder. Pattern types: AB Parallel, A+ Heading, Fixed Contour, Pivot, "Ultimate Curve" (mapping to ISO enum untested).
- **mojoMINI:** only "data export to KML" confirmed; import capability **UNCERTAIN** — do not assume parity with mojo3D.

### 2.9 AGCO (Fendt / Massey Ferguson / Valtra)

All AGCO marques share a "Fuse" backend (Fendt VarioDoc/FendtONE, MF TaskDoc/Agro Link, Valtra TaskDoc), ISOBUS TC-BAS/TC-GEO capable, exchanging ISOXML TASKDATA via USB or AGCO Cloud.

- **Fendt** — generational split: older Vario (SCR/S4) terminals use a proprietary **KML+INI ZIP per field piece** (not ISOXML). FendtONE/VarioDoc (terminal SW ≥ 7.84, USB transfer activated in VarioDoc) imports ISOXML — packaged as **`TASKDATA.zip` containing TASKDATA.xml** (the one brand documented to want a zip). **Curve limitation (forum-verified):** FendtONE cannot import a continuous curved line around obstacles; curves need manual driving or the paid Contour Assistant (~€1000). Straight AB and boundary-derived contour segments work.
- **Massey Ferguson** (Datatronic 5 / Fieldstar 5): officially "ISOXML 3, ISOXML 4 & Shapefile compatible" via MF TaskDoc; in-cab "MF Go Mode" wizard for AB/A+/contour-segment creation. MF hosts the **NEXT Wayline Converter Tool** — converts **straight waylines and boundaries only** between AGCO, John Deere, Topcon, CNH, Trimble, and ISOXML ("AB contours and curves are not displayed or supported" — the OEM's own verdict on curve portability).
- **Valtra** (SmartTouch): TaskDoc/ISOXML, Guide "GO! Mode"; USB specifics assumed identical to Fendt/MF — **UNCERTAIN** for Valtra-specific quirks.
- **Legacy C1000/C2000/C2100/C3000 terminals:** generic Task Controller → Data Transfer → "Import from USB/SD" reading TASKDATA from stick root (import **overwrites** terminal data). Whether they accept v4 GGP/GPN or only v3 — UNCERTAIN.

### 2.10 CLAAS

**Terminals:** CEBIS (machine console; ISOBUS implement operation but no Task-Controller guidance management), GPS PILOT S7 (steering-only), S10 (full ISOBUS/TC terminal, TC-GEO), CEMIS 1200 (current generation).

- **S10:** ISOXML import requires an **active TC-BAS license** (an "AUFTRÄGE"/Orders menu appears when enabled). USB must carry a **plain uncompressed folder named TASKDATA** with TASKDATA.xml — zips must be extracted first. Shapefile import/export available depending on activation.
- **CEMIS 1200:** ISOXML via TC-BAS, FAT32 USB; 2026-dated CLAAS tutorials indicate **newly added native shapefile import** (inferred from video titles — verify).
- Cloud: a CLAAS developer-portal page "CLAAS TELEMATICS ISO-XML export" exists (api-int.claas.com) — content unreachable this session; schema/auth **UNCERTAIN**.
- Curve/pivot GPN rendering fidelity on CLAAS terminals: unverified either way.

### 2.11 Kverneland / Kubota (IsoMatch)

Kubota owns Kverneland (2012); Kubota-badged IsoMatch Tellus GO/GO+ are the same stack. Terminals: IsoMatch Tellus GO/GO+/PRO + IsoMatch GEOcontrol app. Exchange is USB ISOXML: `taskdata` folder at USB root containing **exactly one XML** plus one `.bin` per prescription map (lowercase per the source; treat as uppercase-safe — UNCERTAIN on case sensitivity). GPN guidance-import fidelity unverified. IsoMatch InLine is a manual light-bar (assumed no file import — UNCERTAIN).

### 2.12 Müller-Elektronik (now PTx Trimble GmbH)

Corporate note: AGCO acquired 85% of Trimble Ag (closed 2024-04-01) forming PTx Trimble; Müller-Elektronik GmbH was renamed **PTx Trimble GmbH** (June 2024) — TRACK-Guide/TOUCH products are now AGCO-affiliated.

**Terminals:** TOUCH800/TOUCH1200 (full ISOBUS UT), TRACK-Guide II/III (guidance-focused). Apps: TRACK-Leader (guidance), SECTION-Control, **ISOBUS-TC** (task controller / import bridge).

**USB layout & steps (two independent sources):** root folder **`Taskdata`** containing **`Taskdata.xml`** (+ `GRD00001.BIN` only for VRA maps — guidance-only exports need just the XML). First-run gotcha: the ISOBUS-TC app must first **create the Taskdata folder itself** (Settings → "Create Taskdata folder"); in advanced mode all buttons except Settings are greyed out until then. Alternative shapefile route: `Shp` folder, WGS84, via the free "SHAPE-ISO-XML Converter" (requires ~1-business-day manufacturer activation). ISOBUS-TC has standard vs **extended mode** — extended mode is needed for ISO-XML task processing. Whether TRACK-Leader picks up GPN patterns from imported tasks: plausible, **UNCERTAIN**.

**CCI terminals** (CCI 800/1200; used by Kuhn, Lemken, Amazone, Krone): TASKDATA folder at USB root, **zipped or unzipped accepted**, FAT32; import via CCI.Control; guidance display via CCI.Command (GPN fidelity plausible, unverified).

---

## 3. Universal Formats

### 3.1 ISOXML (ISO 11783-10 / TASKDATA) — Deep Dive

**What it is:** the file-exchange half of ISOBUS. Official **XSDs are free** at isobus.net (`ISO11783_TaskFile_V4-3.xsd`, `_Common_V4-3.xsd`, `_TimeLog_V4-3.xsd`, `_LinkListFile_V4-3.xsd`; also V3-3 and V2-1), even though the prose standard (ISO 11783-10:2015) is paywalled. All structural claims below were verified against the actual XSDs during this research; a minimal AB-line file validated with **zero errors**.

**Version split (critical):**
- **V2/V3.3** (`VersionMajor="3"`): **no GGP/GPN at all.** Guidance is only expressible as a bare `LSG A="5"` ("GuidancePath") directly under `PFD`, PNT PointType limited to 1–2, A/B endpoints distinguished by the PNT Designator attribute (`B="A"`/`B="B"`). Real hardware still emits this (Outback MAX exports v2.0 exactly this way), and many fielded terminals only accept ≤ v3.3.
- **V4.3** (`VersionMajor="4"`): adds GGP/GPN/BSN/GAN/GST, LinkList, guidance point types 6–9, more polygon/linestring types.
- **Exporter policy: emit both dialects** — v4 GGP/GPN for modern terminals, v3-flat fallback for legacy ones.

**Hierarchy (v4):** `PFD` (Partfield) → `GGP` (GuidanceGroup: A=id `GGP1`, B=name; children: 1+ GPN, optional PLN) → `GPN` (GuidancePattern) → exactly one `LSG A="5"` of `PNT` points, optional PLN.

**GPN attributes (XSD-verified):**

| Attr | Name | Req | Values |
|---|---|---|---|
| A | GuidancePatternId | yes | `(GPN\|GPN-)[0-9]+`, unique file-wide |
| B | Designator | no | ≤32 chars, farmer-visible name |
| C | **GuidancePatternType** | yes | **1=AB, 2=A+, 3=Curve, 4=Pivot, 5=Spiral** |
| D | Options | no | 1=CW, 2=CCW, 3=FullCircle (pivot) |
| E | PropagationDirection | no | 1=both, 2=left, 3=right, 4=none |
| F | Extension | no | 1=both ends, 2=from A, 3=from B, 4=none |
| G | Heading | no | decimal **0–360 degrees** (A+ patterns). ⚠ Conflict: one stream cited radians "per ISO convention"; the XSD-verified range 0–360 supports degrees — but always supply real point coordinates so displays can derive heading geometrically |
| H | Radius | no | uint; pivot radius; unit believed **mm** (UNCERTAIN — XSD gives no unit; one stream confirmed ADAPT exporter converts to mm) |
| I | GNSSMethod | no | 1 GNSS…5 RTK-float, 7 Manual, 8 Simulate, **16 = Desktop generated data (use this)**, 17 Other |
| J/K | Horiz/VertAccuracy | no | 0–65 m |
| L | BaseStationIdRef | no | → BSN |
| M | OriginalSRID | no | ≤32 chars, informational CRS tag |
| N/O | NumberOfSwathsLeft/Right | no | uint |

**PNT (Point):** A=PointType (v4: …6=GuidanceReferenceA, 7=GuidanceReferenceB, 8=GuidanceReferenceCenter, 9=GuidancePoint), B=Designator, **C=PointNorth (lat, −90..90), D=PointEast (lon, −180..180)** — WGS84 decimal degrees, ≤9 fraction digits, E=PointUp (mm). **⚠ Conflict on point-typing convention:** the ADAPT test fixture uses generic type 2 + "start"/"end" designators; ADAPT production code tags curve vertices as 9; the semantic convention is 6 (A) / 7 (B) / 8 (pivot center). **Recommendation:** type AB endpoints 6/7 (safest semantically); for v3 fallback use type 2 with Designator "A"/"B" as real Outback hardware does. Which convention each brand's importer requires is untested.

**LSG LineStringType:** 1 PolygonExterior, 2 PolygonInterior, 3 TramLine, 4 SamplingRoute, **5 GuidancePattern** ("GuidancePath" in v3), 6 Drainage, 7 Fence, 8 Flag, 9 Obstacle. `LSG C` = width in mm (usable as swath-width hint; don't rely on it surviving import).

**Pattern drawing:** AB = 2 PNT (types 6,7). A+ = 1 PNT (type 6) + G heading. Curve = full polyline (first 6, middles 9, last 7 — convention, not schema-enforced). Pivot = PNT type 8 + optional H radius + D option, or 3 points (center, start, end). Note: **GPN carries no implement width** — track spacing comes from terminal implement setup.

**Task linkage:** `TSK A B C=CTRref D=FRMref E=PFDref G=1(Planned)`; v4 optionally `GAN` (GuidanceAllocation, A=GGP ref) with `GST` (GuidanceShift: east/north shift in mm — how terminals record nudges). GAN not required for lines to be usable, but a Planned TSK referencing the PFD smooths import on task-centric terminals (CCI/ME/CNH).

**Minimal TASKDATA.XML with one AB line — validated 0 errors against the official ISO11783_TaskFile_V4-3.xsd:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ISO11783_TaskData VersionMajor="4" VersionMinor="3"
                   ManagementSoftwareManufacturer="LINEGUIDER"
                   ManagementSoftwareVersion="1.0"
                   DataTransferOrigin="1">
  <CTR A="CTR1" B="Siebert Farms"/>
  <FRM A="FRM1" B="Home Farm" I="CTR1"/>
  <PFD A="PFD1" C="North 80" D="323749" E="CTR1" F="FRM1">
    <PLN A="1" B="North 80 boundary" C="323749">
      <LSG A="1">
        <PNT A="2" C="-23.550000000" D="-51.480000000"/>
        <PNT A="2" C="-23.550000000" D="-51.470000000"/>
        <PNT A="2" C="-23.558000000" D="-51.470000000"/>
        <PNT A="2" C="-23.558000000" D="-51.480000000"/>
        <PNT A="2" C="-23.550000000" D="-51.480000000"/>
      </LSG>
    </PLN>
    <GGP A="GGP1" B="North 80 lines">
      <GPN A="GPN1" B="AB main" C="1" E="1" F="1">
        <LSG A="5">
          <PNT A="6" C="-23.550500000" D="-51.479500000"/>
          <PNT A="7" C="-23.557500000" D="-51.479500000"/>
        </LSG>
      </GPN>
    </GGP>
  </PFD>
  <TSK A="TSK1" B="Plant North 80" C="CTR1" D="FRM1" E="PFD1" G="1">
    <GAN A="GGP1">
      <GST A="GGP1" B="GPN1"/>
    </GAN>
  </TSK>
</ISO11783_TaskData>
```

**V3.3 fallback equivalent** (also XSD-validated): same skeleton with `VersionMajor="3" VersionMinor="3"`, no GGP/GPN — instead directly under PFD:
```xml
<LSG A="5" B="AB main">
  <PNT A="2" B="A" C="-23.550500000" D="-51.479500000"/>
  <PNT A="2" B="B" C="-23.557500000" D="-51.479500000"/>
</LSG>
```

**Multi-file layout** (what real Outback/AgJunction hardware emits): root TASKDATA.XML holds only `<XFR A="PFD00000" B="1"/>` stubs; content lives in `PFD00000.xml`, `CTR00000.xml`, … each wrapped in `<XFC>`. Support reading both; write inline-monolithic by default (some terminals handle XFR poorly), multi-file when targeting Outback.

**TLG binary time-logs (ingest side):** `TLG#####.XML` header = one `TIM` (Type D="4" Effective) whose **empty-string attributes mean "value stored per-record in the paired .BIN"**; `.BIN` records are little-endian: `uint32` ms-since-midnight + `uint16` days-since-1980-01-01, then only the declared-empty PTN fields (lat/lon `int32` × 1e-7 deg, up `int32` mm, status `uint8`, PDOP/HDOP `uint16` × 0.1, sats `uint8`, GPS time `uint32`/date `uint16`), then `uint8` DLV count + per-DLV (`uint8` header index + `int32` value; DDIs as 2-byte hexBinary, e.g. `008D` = Actual Work State). Caution: `robolibs/taskmap`'s described TLG layout (32-byte "TLG\0" header) is **non-canonical** — do not use it as a reference.

**Universal packaging & common failure modes (dev4agriculture troubleshooting + OEM docs):**
1. FAT32 USB; folder literally `TASKDATA` (all-caps; case-sensitive on many terminals) at the **root**; file exactly `TASKDATA.XML`.
2. #1 real-world failure: Windows hides extensions → users create `TASKDATA.XML.xml`. Write and verify names programmatically.
3. Must be a real folder, not a zip — **except Fendt classic** (wants `TASKDATA.zip`) and CCI (accepts both).
4. Many embedded terminals accept only ≤ v3.3 → offer version-downgrade (drop GGP/GPN, flat style).
5. Keep files small (< ~100 KB for old terminals); strip unused coding data; UTF-8 mandatory; ASCII designators (no umlauts — CNH explicitly warns); strip proprietary `P###` elements for cross-brand exports.
6. IDs globally unique across the whole file (single global counter — the exact bug ADAPT ISOv4Plugin hit in issue #95 and AgOpenGPS fixed in 6.8.2). Positive IDs = FMIS-authored; negative = terminal-authored. `DataTransferOrigin="1"`.
7. Re-import hygiene: strip TIM/TLG/allocation stamps, reset TaskStatus to 1 (Planned), re-issue IDs before re-sending used TASKDATA (terminals may reject/duplicate otherwise).

**Validators/tooling:** AEF Taskdata Validator (inside aef-isobus-database.org; also use the AEF database to check per-model/per-firmware TC-BAS/TC-GEO certification); plain XSD validation (proven with Python `xmlschema`); isoxml.tools (browser editor + best free element docs); dev4Agriculture Analyzer/Viewer/Anonymizer.

**Libraries:**
| Library | Language | License | Notes |
|---|---|---|---|
| dev4Agriculture `isoxml` (npm) | TypeScript | Apache-2.0 | All v4.3 entities incl. GGP/GPN; reads/writes v3 & v4 with conversion; TLG binary parsing; browser + Node — best fit for a JS/TS product |
| dev4Agriculture `isoxml-dotnet` (NuGet) | C#/.NET | Apache-2.0 | TASKDATA + TimeLog + Grid + LinkList + guidance; V3↔V4; TC emulation |
| AgGateway ADAPT `ISOv4Plugin` | C# | EPL-1.0 | Reference implementation; full guidance mappers + real test fixtures; watch for duplicate-ID bug (#95) |
| `isoxml` (PyPI, Josephinum-Research) | Python | Apache-2.0 | v3+v4 models, shapely/numpy helpers; no documented TLG binary support |
| AgOpenGPS ≥ 6.8.x | C# | open | Working reference exporter real terminals accept (incl. a Raven dialect); live compatibility log on its forum |

**Terminal ISOXML-guidance support matrix (evidence-graded):**

| Terminal | TASKDATA import | GPN guidance import | Confidence |
|---|---|---|---|
| Fendt Vario/FendtONE (SW≥7.84) | yes (TASKDATA.zip) | yes — straight waylines confirmed; curves fail | HIGH |
| Outback MAX/STX (S3) | yes (auto-prompt) | yes — **v2 flat style** (verified from real device output) | HIGH |
| CNH Pro 700/IntelliView IV | yes (documented, v3-era) | AB via v3 GuidancePath (community-reported) | MEDIUM |
| CNH Pro 1200/IntelliView 12 | yes | expected (native ISOXML platform) | MEDIUM-HIGH |
| CCI 1200 (Kuhn/Lemken/Amazone) | yes | plausible | MEDIUM |
| CLAAS S10/CEMIS 1200 | yes (TC-BAS license) | unverified | MEDIUM |
| MF/Valtra (TaskDoc) | yes (ISOXML 3+4) | straight lines expected | MEDIUM |
| Müller TRACK-Guide/TOUCH | yes (Taskdata folder, extended mode) | plausible/UNCERTAIN | LOW-MED |
| Trimble Precision-IQ | yes (convert-to-AgData flow) | guidable line-sets confirmed; GPN fidelity untested | MEDIUM |
| Raven Viper 4 / CRX | yes (KB workflows) | UNCERTAIN | LOW |
| Topcon Horizon (X25+) | yes (spec sheet) | contradicted by field reports — test | LOW |
| Kverneland IsoMatch | yes | UNCERTAIN | LOW |
| John Deere Gen4/G5 | yes (18-2+, TC-GEO, EU activation) | **assume NO** — guidance absent from Deere's supported list | HIGH (for the caveat) |

### 3.2 Shapefile Guidance Spec

**Who accepts a shapefile as a guidance line:** natively only **Trimble legacy** (per-field guidance shapefile; replace-not-merge) and **Leica mojo3D** (wayline import). CNH Pro 700 accepts "Multiswath guidance lines" via its `Shapefile` USB folder, but the required DBF schema is undocumented (obtain a real AFS/SMS export and reverse it). JD and Raven reject shapefile guidance outright; Ag Leader requires manual conversion through SMS; Topcon and Outback accept shapefiles for boundaries/Rx only. **Pivot/circle guidance has no shapefile representation anywhere.**

**Format essentials (ESRI 1998 whitepaper, GDAL, corroborated):**
- Three required siblings sharing a basename: `.shp` (geometry), `.shx` (index), `.dbf` (dBase attributes, one record per shape, same order). Optional: `.prj` (WKT CRS — effectively required for ag displays), `.cpg`, spatial indexes.
- `.shp` 100-byte header: file code 9994 (big-endian), file length in **16-bit words** (big-endian — classic bug), version 1000 + shape type + bbox (little-endian). **PolyLine = type 3**: bbox + NumParts + NumPoints + Parts[] + Points[] (X=lon, Y=lat doubles).
- **DBF field-name limit is 10 characters** (not 13 — the "13" figure conflates the default *width* of numeric fields). Max 255 fields; numeric values stored as ASCII text; `D` dates have no time component; weak Unicode.
- **No CRS in shp/shx/dbf** — a missing/wrong `.prj` fails silently. Ag displays overwhelmingly expect **WGS84 geographic (EPSG:4326)**; always reproject before export and let a library write the `.prj` (ESRI vs OGC WKT flavors differ cosmetically).
- Multipart PolyLine (NumParts>1) is legal per spec but **no vendor documents whether display firmware tolerates it** for guidance — emit one simple record per line and test.
- Zipping: JD Rx requires a zip containing an `Rx` folder; CNH wants an unzipped `Shapefile` root folder; Trimble wants unzipped triplets in the right tree — folder naming is brand-exact.

**Libraries:** write side — GDAL/OGR (most robust: name truncation/dedup, `.shz` zips, CRS handling), GeoPandas (auto-`.prj` from `gdf.crs` — set/convert to EPSG:4326 first), pyshp (pure Python; does NOT auto-write `.prj`), `@mapbox/shp-write` (browser, GeoJSON→zip, STORE compression). Read side — `shpjs` (auto-reprojects to WGS84 using embedded `.prj`), Bostock's `shapefile` npm (streaming, read-only).

---

## 4. Deriving Lines from Machine Data

### 4.1 Ingestible pass-level data sources

| Source | Format | Pass-level GPS? | Key attributes |
|---|---|---|---|
| JD Operations Center | zipped point shapefiles (WGS84) | yes, ~1 Hz | heading (deg), distance/sample, swath width, timestamp, yield/moisture; 250-operation export cap; free samples at `github.com/JohnDeere/SampleData` |
| ISOXML terminals | `TASKDATA/` TLG XML+BIN pairs | yes | lat/lon ×1e-7, DDI values (work state, width); fully open — see §3.1 |
| Ag Leader | `.agdata` (opaque) → SMS "Advanced" text export | yes | classic record carries **pass number natively**, flow, swath, moisture, heading via positions (verify column order vs Yield Editor docs) |
| Climate FieldView | `.dat` (closed; Data Manager → Export DAT Files) | yes but closed | readable only via Climate's FODD ADAPT plugin; public API exports planting *summaries* (GeoJSON MultiPolygon) only |
| Precision Planting 20\|20 Gen3 | `.2020` | yes, 1/5 Hz | free (closed-binary) .NET ADAPT plugin `PrecisionPlanting.ADAPT._2020.Plugin` |
| CNH | `.cn1` folder | yes but closed | gated CN1 SDK / CN1 ADAPT plugin (CNH Developer Portal) |
| Generic NMEA/CSV loggers | GGA/RMC/VTG | yes, 1–10 Hz | no swath width — infer or ask user |

GeoPard's import list is a realistic checklist of what farmers hand over: shapefile, ISOXML, `jdl` (JD), `cn1` (CNH), `adm` (Ag Leader), `dat` (FieldView/PP). ADAPT (AgGateway) is the practical translation layer — but the JD/CNH/AgLeader/Climate/PP plugins are free **closed .NET binaries**, forcing a .NET sidecar in a Node/Python backend.

### 4.2 Algorithm pipeline (coverage points → guidance lines)

1. **Preprocess** (validated by the 2026 Frontiers plant-science pipeline, 96.3% field-vs-road accuracy): drop missing/duplicate points; speed-band filter (working ≈ 4–12 km/h); static-drift detection; interpolate small gaps. Expect GPS-vs-measurement lag (grain flow lags ~10–12 s in harvest data — prefer planting/application data; USDA Yield Editor's flow-delay and start/end-pass filters exist for exactly these artifacts).
2. **Collapse section rows to machine centerline** (JD exports emit one point per section per instant — group by timestamp and average).
3. **Pass segmentation:** sort by time; split on time gaps (> 3–5× sampling interval), sustained heading change (turn detection via unwrapped heading derivative), and speed drops. Classify: long consistent-heading segments = passes; short high-curvature = headland turns; fast straight = road. Ag Leader Advanced text already carries pass numbers.
4. **Straight AB fit:** per-pass **PCA / total least squares** (orthogonal regression — error in both coordinates); trim turn-in/out points; robustify with RANSAC. **Dominant heading** via length-weighted circular statistics with 180° axial ambiguity handled by angle-doubling (mean of 2θ). Multi-modal heading histogram ⇒ multiple guidance groups (L-shaped fields) — cluster passes by heading mode, one AB per cluster. Fallback candidate: longest boundary edge (Ohio State factsheet confirms farmers' lines historically follow it; SMS's boundary wizard got within 2° of GIS-optimal).
5. **Swath-width inference:** perpendicular distances between adjacent same-heading pass centerlines → histogram **mode/median** (robust to overlap/skip); cross-check against SWATHWIDTH columns (distrust harvest values — "wandering swath width syndrome"); detect w/2w peaks for skip-pass patterns.
6. **Curves:** centerline → Ramer–Douglas–Peucker decimation → cubic-spline smoothing (C1/C2); cap curvature at machine turning radius. Preferred alternative to offsetting: **pick the best recorded pass as the master curve** and let the display propagate — displays store one curve per pattern anyway.
7. **Offsets (when needed):** compute in a local metric CRS (UTM/local tangent), convert back to WGS84. Engines: GEOS ≥ 3.11 / Shapely 2 `offset_curve` (positive=left; post-clean self-intersections by noding + dropping loops, or offset iteratively from the previous cleaned offset); JTS `OffsetCurve` (same semantics; flat-line artifacts at large offsets); **Clipper2 is the wrong tool** for one-sided open-path offsets (produces closed buffer outlines; cannot shrink open paths); turf.js `lineOffset` does not clean self-intersections. Note most displays generate parallels themselves — usually export ONE reference line + width.
8. **Headland detection:** passes whose mean distance-to-boundary < ~1.5–2× swath and whose heading tracks the boundary tangent; boundary from imported polygon or concave hull (alpha-shape) of coverage.
9. **Coordinate hygiene:** all export in WGS84 decimal degrees; if targeting AgOpenGPS's local-meters format, apply origin offsets **and the UTM grid-convergence angle** stored in its Field.txt (forum-confirmed failure mode when omitted).

### 4.3 Prior art & libraries

- **John Deere AutoPath** — the commercial embodiment of "derive guidance from operation data" (implement-mounted StarFire row recordings → Operations Center → whole-field guidance for later ops at any width); requires SF3+ and a license — proves demand, locked to Deere.
- **Ag Leader SMS** guidance wizard and **GeoPard Guidance Lines Simulator** (AB/curve/boundary-follow/auto-blocks from a *boundary*, exports SHP/GeoJSON/KML) both start from boundaries, **not coverage points** — the coverage-derived niche is open.
- **Fields2Cover** (BSD-3, C++17 + Python bindings): the strongest open geometry engine for the swath side — headland generation, swath-angle optimization (coverage/#swaths/overlap objectives), route ordering, Dubins/Reeds-Shepp smoothing — but boundary-driven, not point-driven.
- **AgOpenGPS field format** (verified from source): `Field.txt` (origin offsets, UTM zone, convergence angle, StartFix), `ABLines.txt` (`Name,heading-deg,easting,northing` in field-local meters), `CurveLines.txt` (per-curve blocks with per-point easting/northing/heading); imports KML AB lines.
- **No public open-source project goes directly "coverage points → AB line file."** Nearest blocks: Fields2Cover, academic field-road segmentation, USDA Yield Editor (pass-aware cleaning; imports Ag Leader Advanced + Greenstar text), cleanRfield (R).

---

## 5. Ecosystem / Competitor Landscape

*(Synthesized from cross-mentions in the nine complete research streams; the dedicated ecosystem stream was truncated — treat as partial.)*

**OEM cloud platforms (the incumbents LINEGUIDER routes around or into):**
- **John Deere Operations Center** — dominant; guidance lines via manual UI or gated JSON API (AB-only creation); Data Sync/AutoPath make USB increasingly optional on connected JD fleets.
- **PTx Trimble FarmENGAGE** (ex-Trimble Ag Software) — the closest thing to a universal hub: imports/exports guidance lines across Shapefile, KML, ISOXML, AgData/AgGPS, JD, CNH `.cn1`, Raven, Ag Leader; API sync with JD Ops Center, CNH FieldOps, Raven Slingshot, agrirouter. Its existence validates the multi-format concept and is also the strongest competitor.
- **CNH AFS Connect / MyPLM Connect**, **Raven Slingshot** (`.ssa`, `/JobData` zip API), **Ag Leader AgFiniti** (wireless `.agsetup`/`.agdata`, in-cloud Guidance Line Management, remote display control), **Topcon TAP**, **CLAAS connect/Telematics**, **AGCO Cloud**, **agrirouter** (DKE — neutral machine↔FMIS taskdata transport, EU-centric).

**Cross-brand converters (direct functional competitors):**
- **AGCO/NEXT Farming Wayline Converter** — free web tool converting waylines between AGCO, JD, Topcon, CNH, Trimble, ISOXML — **straight AB + boundaries only**, explicitly no curves; requires data "directly from the terminal." The strongest signal of both demand and the curve-portability ceiling.
- **Ag Leader SMS Basic/Advanced** (~$750/$1995 + annual support) — broadest desktop hub (reads/writes JD, CNH, Trimble, Raven, AGCO, CLAAS, etc.; guidance exports PAT/GLN/FLD/Trimble/RDL) but requires manual per-field GUI work; no automation/API.
- **Trimble Farm Works** — legacy decode bridge (reads GS2 `Setup.fds`, decodes Precision-IQ→legacy transfers).
- **isoxml2shape.com** (Agrinavia), **isoxml.tools** (browser ISOXML editor), **dev4Agriculture** tool suite — free ISOXML utilities, none guidance-derivation-focused.

**Open-source adjacent:** AgOpenGPS (free guidance software + ISOXML export, active community compatibility log), Fields2Cover, ADAPT Framework (AgGateway; industry translation layer — JD is a founding member; Trimble/CNH ship official plugins), QGIS/GeoDataFarm.

**Positioning takeaway:** nobody ships "upload your monitor data → get derived AB lines back in every brand's native import package with instructions." FarmENGAGE converts but doesn't derive; AutoPath derives but is JD-locked; SMS does both poorly-automated behind a desktop GUI. That intersection is LINEGUIDER's open niche.

---

## 6. Recommended Format-Support Matrix for LINEGUIDER v1

| Display / target | Best export format (v1) | Confidence | Difficulty |
|---|---|---|---|
| **Outback MAX/STX (S3)** | ISOXML **v2 flat** multi-file (`LSG A="5"`, PNT Designator A/B) in `TASKDATA/` | High (verified vs real device export) | Low |
| **CNH AFS Pro 1200 / IntelliView 12** | ISOXML v4 GGP/GPN, `TASKDATA/TASKDATA.XML` | High | Low–Medium |
| **Fendt FendtONE / VarioDoc (SW≥7.84)** | ISOXML v4, packaged as `TASKDATA.zip` — **straight AB/A+ only** | High | Low–Medium |
| **Massey Ferguson / Valtra (TaskDoc)** | ISOXML v3 + v4 `TASKDATA/` | Medium-High | Low–Medium |
| **CLAAS S10 / CEMIS 1200** | ISOXML v4, unzipped `TASKDATA/` (TC-BAS license note in instructions) | Medium-High | Low–Medium |
| **Trimble Precision-IQ (GFX-350/750/1060/1260, TMX-2050)** | ISOXML v4 at USB root → documented convert-to-AgData flow; guidable line-set fallback | Medium-High | Medium |
| **CCI terminals (Kuhn/Lemken/Amazone)** | ISOXML v4 `TASKDATA/` (zip or folder) | Medium | Low–Medium |
| **Müller-Elektronik TRACK-Guide/TOUCH** | ISOXML `Taskdata/Taskdata.xml` (+ folder-creation instruction) | Medium | Medium |
| **Kverneland/Kubota IsoMatch Tellus** | ISOXML `taskdata/` (exactly 1 XML) | Medium | Medium |
| **Leica mojo3D** | **KML** (and/or WGS84 shapefile set incl. `.prj`) wayline | High | Low |
| **CNH AFS Pro 700 / IntelliView IV** | ISOXML **v3 flat** (`TASKDATA/`, SW-version note 31.26/31.31) + `Shapefile`-folder Multiswath as secondary | Medium | Medium–High |
| **John Deere (Gen4/G5 + Operations Center)** | Operations Center Guidance Lines API — **straight AB only** — plus generated manual-entry instructions (2 points + heading) for curves/pivots | High (mechanism) | Medium–High (partner API approval) |
| **John Deere GS2/GS3 legacy** | No file path — manual-entry instructions only | High (negative) | N/A |
| **Topcon X25/X30/X35/XD** | ISOXML v4 (flagged experimental; empirical testing required) | Low–Medium | Medium |
| **Raven CR7/CR12 (CRX)** | ISOXML (flagged experimental; consider AOG's "Raven dialect" quirks) | Low–Medium | Medium |
| **Raven Viper 4** | Not supported in v1 (proprietary `.ab`; ISOXML GPN unverified) — manual instructions | High (negative) | Very High |
| **Ag Leader (InCommand/Integra)** | Not supported in v1 (`.agsetup` undocumented) — SMS/manual-entry instructions; monitor AgFiniti API | High (negative) | Very High |
| **All brands (universal fallback)** | WGS84 line shapefile + KML download + per-brand printed instructions | High | Low |

**v1 engineering priorities:** (1) one ISOXML generator with v4-GGP/GPN and v3/v2-flat emit modes + per-brand packaging profiles (zip vs folder, monolithic vs multi-file, filename casing); (2) XSD + AEF-validator gate in CI; (3) KML/shapefile writers for mojo3D and universal fallback; (4) JD API integration (AB-only) behind partner approval; (5) curve export gated behind an explicit "may not import — recreate by hand on some terminals" warning with dense-polyline decomposition.

---

## 7. Open Questions / Risks

**Undocumented formats (reverse-engineering exposure):**
1. JD GS2/GS3 `RCD`/`Setup.fds` and Gen4/G5 USB setup payloads — no public schema; firmware churn documented (25.3 dropped legacy imports). Do not attempt to write.
2. Ag Leader `.agsetup`/`.agdata` — no public structure, no OSS parser; `.pat` bridge format also undocumented.
3. Raven `.ab` — binary internals unknown; Envizio guidance extension unconfirmed.
4. Topcon native AB-line format — no public extension/spec (AGCO's converter proves it's crackable, but privately).
5. CNH Multiswath shapefile `.dbf` schema — undocumented; needs a real AFS/SMS export sample.
6. Trimble `.agf` — encrypted; open decoder handles polygons only; cited AES key unverified.

**Standards/verification gaps:**
7. GPN Heading unit (degrees 0–360 per XSD vs "radians" claim), Radius unit (mm assumed), and PNT PointType convention for AB endpoints (6/7 vs 2+designator) — verified against XSD/implementations but not the paywalled ISO text; ship both-safe encodings (real coordinates always present).
8. GPN import fidelity is **untested on real hardware** for Topcon, Raven, Kverneland, Müller/TRACK-Leader, CLAAS, and Trimble Precision-IQ — the single highest-value validation activity before launch is generating test TASKDATA files and importing them on borrowed/dealer hardware (or the JD Display Simulator / AEF validator as proxies).
9. Curve/pivot portability is unreliable industry-wide (AGCO's own tool refuses curves; FendtONE fails; JD API can't create them; no shapefile pivot exists) — v1 must set user expectations explicitly.
10. Cross-brand AB math divergence (JD earth-curvature vs Trimble flat) means identical coordinates ≠ overlapping passes; export per-brand conventions, never promise cross-brand overlay equivalence.

**Licensing / access:**
11. JD Guidance Lines API requires partner registration/approval; ToS constraints on redistribution unexamined.
12. CNH CN1 SDK / CN1 ADAPT plugin are subscription-gated with T&Cs; eligibility/cost for an independent vendor untested.
13. Closed ADAPT plugins (JD, CNH, Ag Leader, Climate FODD, PP .2020) are all .NET binaries — a non-.NET backend needs a sidecar service; redistribution licenses need review.
14. ISO 11783-10 prose standard is paywalled (XSDs free); ADAPT is EPL-1.0 (weak copyleft — check obligations if modified); Fields2Cover BSD-3; dev4Agriculture libs Apache-2.0 (clean).
15. GPL-3.0 components (TwinYields/ISOXML) must stay out of the proprietary codebase or be isolated.

**Testing needs (ranked):**
16. Hardware import tests: Topcon Horizon, Raven CRX, Kverneland, Müller, CLAAS, Trimble Precision-IQ GPN behavior; CNH Pro 1200 on-device import UX; mojoMINI import capability; mojo3D USB folder placement; multipart-vs-single-part PolyLine tolerance for shapefile guidance.
17. Acquire ground-truth samples: real CNH Multiswath shapefile, real Trimble guidance shapefile (DBF schema), real Ag Leader `.agsetup`, real Topcon export, real CNH Pro 1200 TASKDATA export (PointType convention check).
18. Version-churn tracking: JD firmware release notes, CNH 31.x TC behavior switch, CLAAS CEMIS shapefile additions — format-support claims must be firmware-qualified, ideally cross-checked live against the AEF ISOBUS Database rather than hardcoded.
19. Documentation-conflict resolutions: Trimble AgGPS-vs-AgData Prescriptions root; TMX-2050 firmware identity; "AgRemote" (likely nonexistent — drop from product copy).

---

## 8. Full Source List

### Official OEM documentation & developer portals
- https://developer.deere.com/dev-docs/guidance-lines · /files · /boundaries
- https://displaysimulator.deere.com/onscreen_help/4640/current/en/file_manager/ (file_manager.htm, _import_data.htm, _data_types.htm, _data_sync.htm) · /autotrac_guidance/guidance_create_track_ab_curve.htm
- https://displaysimulator.deere.com/artifacts/desktop/en/Display_and_CommandARM_Sim_OFFline_Guide_EN.pdf
- https://www.deere.com/assets/pdfs/common/stellarsupport/18-2_Gen4_CommandCenter_NewFeatures_English.pdf · 23-1-gen-5-release-notes-english.pdf · Gen4CommandCenter_ReleaseNotes_16-1_English.pdf
- https://processes.premiercrop.com/hubfs/Rx_JD2600_2630.pdf (JD/Premier Crop Rx guide)
- https://mmcjd.com/img/PDF/OperationsCenter/Operations%20Center%20-%20Guidance%20Lines.pdf
- CFX-750 User Guide v7.0 Rev A — https://modernaginc.com/wp-content/uploads/2016/11/cfx-750-user-guide-7a.pdf
- Precision-IQ Reference Manual v5.60 — https://www.vantage-agrometius.nl/wp-content/uploads/2019/02/Precision-IQ-RefManual_5.60-ENG-min.pdf
- Precision-IQ GFX-750 Guide v2.0 Rev C — https://fairwindfarms.com/wp-content/uploads/Trimble-Precision-IQ-GFX-750_optimized.pdf
- Precision-IQ / TMX-2050 guide — https://modernaginc.com/wp-content/uploads/2016/11/trimble-precision-iq-user-guide-2c.pdf
- https://ptxag.com/us/en/products (GFX/TMX pages) · /digital-farming-solutions/farmengage/farm-data-compatibility · /partners/developers/
- CNH Developer Portal — https://develop.cnh.com/framework-guides/cn1-sdk · /cn1-adapt-plugin · /isoxml-adapt · /troubleshooting/glossary · FAQ pages
- Case IH Shapefile Import doc CIH03291601 — https://d1hu4133i4rt3z.cloudfront.net/attachments/848/848519-….pdf (mirror: processes.premiercrop.com)
- CNH AFS700/IntelliView IV ISOXML procedure (German) — https://static.agrarcommander.at/commander/loginsite/page64/files/HinweisAFS700.pdf
- Ag Leader Compass Operators Manual FW 6.3 — https://maplelanefarmservice.ca/resources/specsheets/precision-ag/agleader/Display_Compass.pdf
- InCommand/Integra manuals via ManualsLib (manualslib.com/manual/1456391, /907412) · release notes at ag-precision.com (InCommand v9.5; Integra/Versa/Compass v7.7)
- https://www.agleader.com/incommand-go/
- Topcon X Console brochure 7010-2147 — https://www.topconpositioning.asia/…/xconsoles_broch_7010_2147_revb_sm_0.pdf
- Raven Viper manual — https://www.manualslib.com/manual/1229781/Raven-Viper.html (pp. 55, 58, 65) · Envizio Pro manual /1199685 · Raven KB (ravenind.my.salesforce-sites.com, titles confirmed)
- Outback support — https://outbackguidance.zendesk.com/hc/en-us/articles/360036635393 (TASKDATA import) · article_attachments/360047443234 (real TASKDATA.zip sample) · STX User Guide 875-0352-000 Rev C1 · MAX firmware table 360019110794
- Leica Mojo 3D manual — https://www.manualslib.com/manual/839855/Leica-Mojo-3d.html
- Fendt/AGCO — https://www.nextfarming.de/hilfe/terminal/fendt-varioterminal/ · /claas-s10/ · /weglinienkonverter/ · https://www.fendt.com/int/smart-farming · https://www.fusesmartfarming.com (MF Guide, task-data-management) · https://www.masseyferguson.com/…/next-wayline-converter-tool.html · https://www.valtra.com/technology/valtraguide.html · Agtron C1000 manual (agtron.com)
- CLAAS — https://api-int.claas.com/devportal/developerguideisoxmlexport (unreachable) · MyEasyFarm tutorials
- Kverneland/Kubota — IsoMatch GEOcontrol manual (cdn-assets.greatplainsmfg.com) · kvernelandgroup.com · kubota-eu.com
- Müller-Elektronik/PTx — https://www.mueller-elektronik.de/pm_manuals/ISOBUS-TC-fuer-Touch-Terminals/en/… · TRACK-Guide III manual (manualslib.com/manual/1323012) · PTx rename announcements (mueller-elektronik.de, topagrar.com)
- CCI 1200 manual — https://www.manualslib.com/manual/1550962/Cc-Isobus-Cci-1200.html

### Standards & schemas
- https://www.isobus.net/isobus/file/supportingDocuments (free official XSDs: TaskFile V4-3/V3-3/V2-1, Common, TimeLog, LinkList, ExternalFile)
- ISO 11783-10:2015 — https://www.iso.org/standard/61581.html (paywalled; iTeh preview: cdn.standards.iteh.ai/samples/61581/…) · ISO 11783-10:2009 v3 text — cdn.standards.iteh.ai/samples/39124/…
- https://isoxml.tools/docs/ (get-started, fundamentals/taskdata-xml, elements/pfd, elements/tsk, reset-to-planned)
- https://www.aef-online.org/aef-news/aef-taskdata-validator.html · https://www.aef-isobus-database.org
- ESRI Shapefile whitepaper (1998) — https://www.esri.com/content/dam/esrisites/sitecore-archive/Files/Pdfs/library/whitepapers/pdfs/shapefile.pdf · https://gdal.org/en/stable/drivers/vector/shapefile.html · https://knowledge.civilgeo.com/gis-shapefile-common-restrictions · ESRI KB 000022868

### Open-source projects & libraries
- https://github.com/ADAPT/ADAPT · /ADAPT/ISOv4Plugin (+ issues #95, #155) · /ADAPT/ADMPlugin · api.github.com/orgs/ADAPT/repos
- https://github.com/dev4Agriculture/isoxml-js · /isoxml-dotnet · https://dev4agriculture.de/isoxml-library/ · /terminal-says-no-first-aid-for-isoxml-imports/
- https://pypi.org/project/isoxml/ · /isoxml-writer/ · github.com/just-read-the-instructions/python-isoxml-writer
- https://github.com/AgOpenGPS-Official/AgOpenGPS (+ releases 6.8.x) · https://discourse.agopengps.com/t/converting-fileds-and-lines-fron-aog-to-isoxml/14661 · /convert-ab-lines-from-trimble-to-agopengps/2906
- https://github.com/aparshin/isoxml-visualization · /TwinYields/ISOXML · /robolibs/taskmap · /FIWARE/iotagent-isoxml · /pvvovan/IsoXml
- https://github.com/Bullhill/agf-converter (Trimble AGF→KML)
- https://github.com/JohnDeere/SampleData
- Fields2Cover · pyshp (github.com/GeospatialPython/pyshp) · @mapbox/shp-write · shpjs (calvinmetcalf/shapefile-js) · mbostock/shapefile · GDAL/OGR · GeoPandas · Shapely/GEOS · JTS · Clipper2
- https://adaptframework.org/trimble-ag-adapt-support/ · https://www.nuget.org/packages/AgGatewayADAPTFramework/ · 2020.ag/adapt-usage (Precision Planting)

### Community / dealer / third-party
- NewAgTalk threads: tid=847214, 644045, 1110919, 587989 (JD); 271228 (EZ-Guide shapefiles); 407583, 514846, 537247 (CNH); 762564 (Raven Viper AB import); 619721 (Topcon X30); 1185510 (Trimble TMX guidance shapefile)
- The Combine Forum (paywalled to fetchers): GS2-lines-to-EZ-Guide-500 (23889), GFX750→SMS (336677), CR8090 IntelliView (356691)
- Agrowissen forum (Fendt curved-line ISOXML thread) · thefarmingforum.co.uk thread 144486
- https://help.agverdict.net/knowledge-base/controllers-and-the-need-for-specific-folder-hierarchy/
- https://support.optisurface.com/articles/239891 · /236810 (Trimble LineFeatures.SHP trick)
- https://vrafy.helpjuice.com/case-ih-and-new-holland-data-export · /agleader-prescription-uploading
- https://help.fieldalytics.com/article/811 · https://pctagcloud-support.freshdesk.com (articles 51000381739, 51000381779)
- https://farmplan.co.uk/…/John-Deere-Gen-4-devices-and-Gatekeeper.pdf
- https://precisionspecs.com/greenstar-3-2630/ · https://datafields.blog/loading-greenstar-setup-files-from-a-mac/
- SMS/Ag Leader ecosystem: martensfarms.com (SMS pricing) · globalagtechinitiative.com · cottongrower.com (SMS compat announcements) · portal.agleader.com (JS-blocked) · knowledgebase.agleader.com (unreachable)
- Trimble AutoSync — no-tillfarmer.com/articles/8765 · uk.ptxtrimble.com/software/autosync/
- Ag Leader AgFiniti — farm-equipment.com/articles/24808 · no-tillfarmer.com/articles/14769 · innotag.com
- eigenbaupf.exagt.de (Müller Taskdata how-to) · blog.spotifarm.fr (Kverneland taskdata note) · agrarheute.com (Fendt import)
- KBS LTER datatable 828 (JD export columns) · Flavio Stutz Medium articles (JD shapefile analysis) · USDA Yield Editor docs · Ohio State factsheet fabe-5531 · Frontiers Plant Science 2026 (10.3389/fpls.2026.1874057) · Comput. Electron. Agric. S0168169921001976, S0168169925002455 · GeoPard docs (docs.geopard.tech) · dev.fieldview.com/export-format/ · Intent Ag FieldView DAT export PDF
- Local artifacts from this research (session scratchpad): real Outback MAX TASKDATA extract; XSD-validated TASKDATA.XML / TASKDATA_V3.XML samples

---

*End of master reference. Sections flagged UNCERTAIN or ⚠ Conflict should be resolved by hands-on hardware testing (§7 item 16–17) before the corresponding export profile is marked "supported" in the product.*
