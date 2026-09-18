"""The page the site serves: tools/build_guide.py.

The procedures are tested elsewhere. These are about the page as a thing a
producer receives -- a link on a phone in a cab -- where the failures are
weight, a layout drawn for a desktop, and a link that loses its answer.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def guide():
    """The build script, loaded as a module. Its data is computed on import;
    nothing is written until build() is called."""
    spec = importlib.util.spec_from_file_location(
        "build_guide_under_test", ROOT / "tools" / "build_guide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _photo_refs(data: dict) -> list[str]:
    refs = []
    for walk in data["walkPhotos"].values():
        for step in walk["steps"]:
            refs += [step["button"], step["screen"]]
    for help_ in data["versionHelp"].values():
        for step in help_["steps"]:
            refs += [step["button"], step["screen"]]
    return [r for r in refs if r]


def test_the_site_page_links_its_photographs_rather_than_carrying_them(guide):
    """Baked in, two photographed displays came to eleven megabytes -- a long
    wait on a cab's signal before the first question shows. The site's page
    names each photograph by address and lets the phone fetch the ones on
    screen."""
    assert not guide.OFFLINE
    refs = _photo_refs(guide.DATA)
    assert refs, "no photographs at all -- the walk-throughs went missing"
    assert all(r.startswith("assets/photos/") for r in refs)
    assert "data:image/jpeg" not in json.dumps(guide.DATA)


def test_every_photograph_the_page_asks_for_is_in_the_repository(guide):
    """Branch-mode Pages serves the repository as it stands, so an address the
    page asks for has to be a file that is committed beside it."""
    missing = [r for r in _photo_refs(guide.DATA) if not (ROOT / r).is_file()]
    assert not missing, "the page asks for photos that are not there:\n  " + \
        "\n  ".join(missing)


def test_the_page_is_a_whole_document_a_phone_can_size(guide, tmp_path,
                                                        monkeypatch):
    """Without the viewport line a phone lays the page out 980 px wide and
    shrinks it -- everything two and a half times too small -- and without a
    doctype the browser drops into quirks mode. Both were missing once, on the
    live site, for weeks."""
    out = tmp_path / "page.html"
    monkeypatch.setattr(guide, "OUT", out)
    guide.build()
    head = out.read_text(encoding="utf-8")[:2000].lower()
    assert head.startswith("<!doctype html>")
    assert 'name="viewport"' in head and "width=device-width" in head
    assert 'charset="utf-8"' in head


def test_a_shared_link_points_at_the_site(guide):
    """A link copied from the page opened as a file would be a file:// address
    on somebody else's phone. The page falls back to the site's address, so
    that address has to be the real one."""
    assert guide.SITE_URL.startswith("https://")
    assert guide.DATA["site"] == guide.SITE_URL


def test_the_doorway_keeps_the_answer_in_the_link():
    """The site's front door redirects to the page, and a shared answer rides
    in the address -- after the ? now, after the # in links sent earlier. A
    meta refresh drops both, so the scripted redirect has to carry them."""
    doorway = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "location.search" in doorway
    assert "location.hash" in doorway
    assert doorway.index("location.replace") < doorway.index('http-equiv="refresh"')


def test_a_shared_link_carries_no_character_a_mail_client_mangles():
    """Gmail wraps every link in a google.com redirect, and a # or & inside the
    target is where that goes wrong: the producer gets Google's "Redirect
    Notice" in their phone's language instead of the answer. So the answers
    are written as a path after a ? -- slashes and nothing else -- and the old
    #e=...&m=... form is only ever read, never written."""
    source = (ROOT / "tools" / "build_guide.py").read_text(encoding="utf-8")
    link_for = source.split("function linkFor")[1].split("\n}\n")[0]
    assert "join('/')" in link_for
    assert "URLSearchParams" not in link_for
    share = source.split("function shareUrl")[1].split("\n}\n")[0]
    assert "'#'" not in share and "'?'" in share
