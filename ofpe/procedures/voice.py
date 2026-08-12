"""What the page says out loud, and the name each recording is filed under.

The page can read the steps to somebody whose hands are inside a machine.
Two things can do the reading. The phone's own speech engine is free and
always current, but it sounds like a phone, and on some Android builds it is
missing altogether -- the interface is there and no voice is behind it, so
the button fails on the first line. Or the lines can be recorded ahead of
time by a real TTS model and played back as ordinary audio.

Recording is possible here only because the text is a closed set. Nothing on
this page is composed at runtime: 342 procedures share 565 distinct lines,
about forty-five minutes of speech, roughly ten megabytes as mono MP3. So
the lines can be rendered once and shipped as files, and a producer
downloads the dozen clips for the procedure on the screen rather than a
hundred megabytes of model. It also works on the phones that have no speech
engine at all, which is the case the browser voice cannot serve.

This module owns two things and the page owns neither: what a step sounds
like when it is spoken, and the file name its recording lives under. If the
page computed either one, the two would drift the first time somebody
adjusted the wording, and the page would ask for recordings that were never
made -- silently, because a missing file just falls back to the phone voice.
Computing the names here and shipping them with the data makes that drift
impossible instead of unlikely.
"""

from __future__ import annotations

import hashlib
import re

from ._core import PROCEDURES

__all__ = [
    "PLACEHOLDER_BACKEND",
    "clip_id",
    "lines",
    "longest_procedure",
    "shippable",
    "spoken",
    "step_prefix",
]

#: The renderer can make tones instead of speech, so the player can be tested
#: where the model weights cannot be reached. Named here because the guide
#: build has to be able to recognise them and refuse.
PLACEHOLDER_BACKEND = "tone"


def shippable(manifest: dict, allow_placeholder: bool = False) -> bool:
    """Whether a set of recordings may go into a built page.

    A page that points at placeholder tones is worse than a page with no
    recordings at all: the fallback to the phone's voice never happens,
    because the files load perfectly -- they simply are not speech. So the
    check is here, in code, rather than in whoever remembers to pass the
    right flag.
    """
    if not manifest.get("clips"):
        return False
    if manifest.get("backend") == PLACEHOLDER_BACKEND:
        return bool(allow_placeholder)
    return True

#: How many characters of the digest name a clip. 2^64 names against 600-odd
#: lines: a collision would need the birthday paradox to work about ten orders
#: of magnitude harder than it does.
_NAME_CHARS = 16


def spoken(text: str) -> str:
    """The step as it should be heard rather than seen.

    «guillemets» mark a button name for the eye; spoken they are noise. A
    backslash is a folder separator, and "GS3_2630, Profile, RCD" is what a
    person says out loud when reading a path to somebody else -- spelling the
    slashes would be worse than useless with a display in front of you.
    """
    text = text.replace("«", "").replace("»", "")
    text = text.replace("\\", ", ")
    return re.sub(r"\s+", " ", text).strip()


def step_prefix(number: int) -> str:
    """The number called out before a step, so a glance is not needed to place it."""
    return f"Step {number}."


def clip_id(line: str) -> str:
    """The file name for a line, derived from the line itself.

    Content-addressed on purpose: editing a step's wording changes its name,
    so the new recording cannot be confused with the old one and the stale
    file is visibly orphaned rather than quietly wrong.
    """
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:_NAME_CHARS]


def longest_procedure() -> int:
    """Step count of the longest procedure -- how far the numbers have to count."""
    return max((len(p.steps) for p in PROCEDURES), default=0)


def lines() -> dict[str, str]:
    """Every line the page can speak, keyed by the name its recording takes.

    Two kinds: the steps themselves, and the "Step 4." called out before each
    one. Keeping the number a separate recording is what lets the steps be
    shared -- the same sentence appears at position 2 of one procedure and
    position 7 of another, and it should be one file, not two.
    """
    out: dict[str, str] = {}
    for n in range(1, longest_procedure() + 1):
        line = step_prefix(n)
        out[clip_id(line)] = line
    for procedure in PROCEDURES:
        for step in procedure.steps:
            line = spoken(step)
            if line:
                out[clip_id(line)] = line
    return out
