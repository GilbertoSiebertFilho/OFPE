"""Every procedure for one display, as a single printable page.

The wizard answers one question at a time, which is right when you have one
question. It is wrong when you are training an operator, putting a laminated
sheet in a cab, or handing a new machine over — for that you want the whole
thing at once, on paper.

This renders exactly that: a standalone HTML document, self-contained apart
from the shared stylesheet, laid out to print. It is a plain server-rendered
page rather than a client-side view because it has to survive being emailed,
saved to disk, and opened on a laptop in a workshop with no network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from .. import procedures as pr
from ..catalog import MonitorProfile

__all__ = ["render_handbook"]


def _section(title: str, items, css_class: str = "") -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{escape(str(i))}</li>" for i in items)
    box = f' class="panelbox {css_class}"' if css_class else ' class="panelbox"'
    return (
        f"<h4>{escape(title)}</h4>"
        f"<div{box}><ul class='procnotes'>{lis}</ul></div>"
    )


def _screen_keys(text: str) -> str:
    """Draw «Label» as a key cap.

    Escaping happens per fragment rather than on the whole string, so the
    guillemets can be found before the text is HTML-escaped and no part of the
    source is ever emitted unescaped.
    """
    out, rest = [], text
    while pr.LABEL_OPEN in rest:
        before, _, rest = rest.partition(pr.LABEL_OPEN)
        label, sep, rest = rest.partition(pr.LABEL_CLOSE)
        out.append(escape(before))
        if not sep:  # unclosed; treat the remainder as plain text
            out.append(escape(pr.LABEL_OPEN + label))
            return "".join(out)
        out.append(f"<b class='key'>{escape(label)}</b>")
    out.append(escape(rest))
    return "".join(out)


def _procedure_block(procedure: pr.Procedure, index: int, version_label: str) -> str:
    objective = pr.OBJECTIVES[procedure.objective]
    confidence_class = {
        pr.Confidence.VERIFIED: "native",
        pr.Confidence.FILE_VERIFIED: "structural",
    }.get(procedure.confidence, "needs_sample")

    facts = []

    def fact(label: str, value: str, code: bool = False) -> None:
        # A field reading "n/a" does not apply to this route; printing it is
        # noise on a page somebody is about to carry to a machine.
        if not value or value.lower().startswith("n/a"):
            return
        rendered = (
            f"<code>{escape(value)}</code>" if code else escape(value)
        )
        facts.append(f"<div><dt>{escape(label)}</dt><dd>{rendered}</dd></div>")

    fact("File format", procedure.file_format)
    if procedure.extensions:
        fact("Extensions", "  ".join(procedure.extensions))
    fact("Exactly where it goes", procedure.media_path, code=True)
    fact("Format the stick as", procedure.filesystem)
    fact("Platform", procedure.platform)
    fact("Allow about", f"{procedure.minutes} minutes")

    steps = "".join(f"<li>{_screen_keys(s)}</li>" for s in procedure.steps)
    caveat = (
        f"<div class='panelbox'>{escape(procedure.confidence.description)}</div>"
        if procedure.confidence is not pr.Confidence.VERIFIED
        else ""
    )

    return f"""
<article class="proc handbook-entry">
  <div class="proc-head">
    <div class="titles">
      <h3>{index}. {escape(objective.label)}</h3>
      <div class="sub">{escape(objective.direction.label)} &middot;
        {escape(procedure.transport.label)}</div>
      <div class="badges">
        <span class="badge {confidence_class}">{escape(procedure.confidence.label)}</span>
        <span class="badge">{escape(version_label)}</span>
      </div>
    </div>
  </div>
  <div class="proc-body">
    {caveat}
    {"<h4>The file</h4><dl class='facts'>" + "".join(facts) + "</dl>" if facts else ""}
    {_section("Before you start", procedure.prerequisites)}
    <h4>Step by step</h4>
    <ol class="procsteps">{steps}</ol>
    {_section("Check it worked", procedure.verify, "good")}
    {_section("Worth knowing", procedure.cautions, "warn")}
    {_section("What usually goes wrong", procedure.common_errors, "bad")}
  </div>
  {"<div class='proc-foot'>Sources: " + escape(" &middot; ".join(procedure.sources)) + "</div>" if procedure.sources else ""}
</article>
"""


def render_handbook(
    monitor: MonitorProfile, version_key: str | None = None
) -> str:
    """Build the full HTML document for one display."""
    version_label = next(
        (v.label for v in pr.versions_for(monitor.key) if v.key == version_key),
        "All software versions",
    )

    blocks: list[str] = []
    contents: list[str] = []
    index = 0
    for direction in pr.Direction:
        in_direction = [
            objective
            for objective in pr.available_objectives(monitor.key, version_key)
            if objective.direction is direction
        ]
        if not in_direction:
            continue
        blocks.append(f'<h2 class="hb-direction">{escape(direction.label)}</h2>')
        for objective in in_direction:
            for transport in pr.available_transports(
                monitor.key, objective.key, version_key
            ):
                resolution = pr.resolve(
                    monitor.key, objective.key, transport, version_key
                )
                if resolution.procedure is None:
                    continue
                index += 1
                contents.append(
                    f'<li><a href="#p{index}">{escape(objective.label)}'
                    f" &mdash; {escape(transport.label)}</a></li>"
                )
                blocks.append(f'<a id="p{index}"></a>')
                blocks.append(
                    _procedure_block(resolution.procedure, index, version_label)
                )

    if not blocks:
        blocks = ["<p>No procedures are recorded for this display yet.</p>"]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(monitor.label)} — data handbook</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body class="handbook">
<div class="hb-wrap">

  <header class="hb-cover">
    <img src="/icons/ui/{escape(monitor.icon)}" alt="">
    <div>
      <h1>{escape(monitor.label)}</h1>
      <p class="hb-sub">Getting data in and out — every documented procedure</p>
      <p class="hb-meta">
        Software version: <strong>{escape(version_label)}</strong><br>
        {escape(monitor.generations)}<br>
        Generated {generated}
      </p>
    </div>
  </header>

  <nav class="hb-toc no-print">
    <h2>Contents</h2>
    <ol>{"".join(contents)}</ol>
  </nav>

  <div class="hb-actions no-print">
    <button class="primary" onclick="window.print()">Print this handbook</button>
    <a class="hb-back" href="/">Back to the guide</a>
  </div>

  {"".join(blocks)}

  <footer class="proc-foot">
    Procedures marked "Confirm the menu wording on the machine" have the right
    structure but exact menu names move between software releases. If a step
    does not match your screen, the file is still correct — look for the
    equivalent option, and tell the office what it actually said.
  </footer>

</div>
</body>
</html>
"""
