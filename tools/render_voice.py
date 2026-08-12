#!/usr/bin/env python3
"""Record every line the guide can speak, once, as an ordinary MP3.

    python tools/render_voice.py --backend kitten --voice Jasper
    python tools/render_voice.py --backend pocket --voice bill_boerst
    python tools/render_voice.py --backend tone            # test fixture only

Why record at all, when browsers have a speech engine: because the engine is
not on every phone, and where it is, it sounds like a phone reading a list.
The lines here are a closed set (see ofpe/procedures/voice.py), so they can
be rendered once by a real model and played back by anything that can play
audio -- no model download, no WebAssembly, no runtime.

The two models this drives are the ones worth having:

  kitten  KittenTTS -- Apache-2.0, ONNX, no torch, and the voices ship inside
          the model, so there is one licence covering the whole thing. The
          default for that reason.
  pocket  Kyutai Pocket TTS -- MIT code, 100M parameters, and a catalogue of
          voices pulled from several speech corpora, each under its own
          licence. Read https://huggingface.co/kyutai/tts-voices before you
          publish anything made with it; the VCTK and Expresso voices are not
          all licensed alike.

Rendering is incremental and content-addressed. A clip is named after the
line inside it, so an edited step gets a new name, its old recording is
orphaned rather than silently stale, and re-running this only synthesises
what is genuinely missing. Changing model or voice, on the other hand,
changes every clip, so that re-renders the lot -- the manifest remembers
which model and voice made what is on disk, and refuses to mix two.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import wave

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from ofpe.procedures import voice as vc  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "voice"
MANIFEST = "manifest.json"

#: Speech, mono, at a bitrate chosen to keep a whole procedure's worth of
#: clips inside a few hundred kilobytes -- which is what a phone on a field
#: signal can actually fetch while somebody stands at the cab door.
MP3_KBPS = 32


# --------------------------------------------------------------------------- #
#  Backends
# --------------------------------------------------------------------------- #

class Kitten:
    """KittenTTS: ONNX, CPU, Apache-2.0, voices bundled with the weights."""

    key = "kitten"
    default_model = "KittenML/kitten-tts-mini-0.8"
    default_voice = "Jasper"

    def __init__(self, model: str, voice: str, clean: bool):
        from kittentts import KittenTTS

        self.tts = KittenTTS(model)
        self.voice = voice
        self.clean = clean
        self.sample_rate = 24000
        self.model = model

    def say(self, line: str):
        # speed 0.95: these are folder names and numbers being followed by
        # hand, not prose being skimmed.
        return self.tts.generate(line, voice=self.voice, speed=0.95,
                                 clean_text=self.clean)


class Pocket:
    """Kyutai Pocket TTS: 100M parameters on torch, streaming, multilingual."""

    key = "pocket"
    default_model = "english"
    default_voice = "bill_boerst"

    def __init__(self, model: str, voice: str, clean: bool):
        from pocket_tts import TTSModel

        self.tts = TTSModel.load_model(language=model)
        self.state = self.tts.get_state_for_audio_prompt(voice)
        self.sample_rate = int(self.tts.sample_rate)
        self.model = f"pocket-tts/{model}"
        self.voice = voice

    def say(self, line: str):
        audio = self.tts.generate_audio(self.state, line)
        return audio.detach().to("cpu").float().numpy().reshape(-1)


class Tone:
    """Not a voice. A placeholder so the player can be tested without weights.

    The model weights live on Hugging Face, which is not reachable from every
    build environment. This backend writes a short tone of about the right
    length for each line, which is enough to drive the page -- clip fetched,
    clip played, next clip queued, highlight moved -- and is obviously not
    speech to anybody who hears it. The manifest records what made it, and
    the guide build refuses to ship a page pointing at tones.
    """

    key = "tone"
    default_model = "tone"
    default_voice = "tone"

    def __init__(self, model: str, voice: str, clean: bool):
        self.sample_rate = 8000
        self.model = "tone (placeholder, not speech)"
        self.voice = "tone"

    def say(self, line: str):
        import math

        seconds = max(0.35, len(line) / 14)
        n = int(seconds * self.sample_rate)
        return [0.25 * math.sin(2 * math.pi * 440 * i / self.sample_rate)
                for i in range(n)]


BACKENDS = {b.key: b for b in (Kitten, Pocket, Tone)}


# --------------------------------------------------------------------------- #
#  Encoding
# --------------------------------------------------------------------------- #

def write_wav(path: pathlib.Path, samples, sample_rate: int) -> float:
    """Write float samples in [-1, 1] as 16-bit mono. Returns seconds."""
    try:  # the models hand back numpy; a per-sample loop over 45 minutes is not free
        import numpy as np

        block = np.asarray(samples, dtype="float32").reshape(-1)
        frames = (np.clip(block, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    except ImportError:
        frames = bytearray()
        for s in samples:
            v = int(max(-1.0, min(1.0, float(s))) * 32767)
            frames += int(v).to_bytes(2, "little", signed=True)
        frames = bytes(frames)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(frames)
    return len(frames) / 2 / sample_rate


def to_mp3(wav: pathlib.Path, mp3: pathlib.Path) -> None:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav),
         "-ac", "1", "-b:a", f"{MP3_KBPS}k", str(mp3)],
        check=True,
    )


# --------------------------------------------------------------------------- #
#  Render
# --------------------------------------------------------------------------- #

def render(backend_key: str, model: str, voice: str, clean: bool,
           out: pathlib.Path, prune: bool, limit: int) -> int:
    cls = BACKENDS[backend_key]
    model = model or cls.default_model
    voice = voice or cls.default_voice
    ext = ".wav" if backend_key == "tone" else ".mp3"

    if ext == ".mp3" and not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed to encode the clips and is not on PATH.")

    lines = vc.lines()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / MANIFEST
    old = {}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())

    # A clip is named after its text, not after the voice that read it, so a
    # change of voice has to clear the floor -- otherwise half the steps come
    # out in one voice and half in another, which is worse than either.
    was = (old.get("backend"), old.get("voice"), old.get("format"))
    now = (backend_key, voice, ext.lstrip("."))
    if old and was != now:
        print(f"voice changed ({was[0]}/{was[1]} -> {now[0]}/{now[1]}); "
              "re-recording everything")
        for f in out.iterdir():
            if f.is_file() and f.name != MANIFEST:
                f.unlink()
        old = {}

    missing = sorted((i for i in lines if not (out / (i + ext)).exists()),
                     key=lambda i: lines[i])
    print(f"{len(lines)} lines, {len(lines) - len(missing)} already recorded, "
          f"{len(missing)} missing")
    if limit and len(missing) > limit:
        print(f"--limit {limit}: doing {limit} of them, leaving "
              f"{len(missing) - limit} for a later run")
        missing = missing[:limit]

    tts = None
    started = time.time()
    if missing:
        print(f"loading {backend_key} ({model}, voice {voice}) ...")
        tts = cls(model, voice, clean)

    clips = dict(old.get("clips", {}))
    with tempfile.TemporaryDirectory() as tmp:
        scratch = pathlib.Path(tmp) / "clip.wav"
        for n, clip in enumerate(missing, 1):
            seconds = write_wav(scratch, tts.say(lines[clip]), tts.sample_rate)
            target = out / (clip + ext)
            if ext == ".mp3":
                to_mp3(scratch, target)
            else:
                shutil.copyfile(scratch, target)
            clips[clip] = {"s": round(seconds, 2), "b": target.stat().st_size}
            done = time.time() - started
            print(f"  [{n}/{len(missing)}] {seconds:5.1f}s  {lines[clip][:60]}"
                  f"   ({done / n:.1f}s/clip)")

    # Anything on disk that no line asks for any more.
    orphans = [f for f in out.glob("*" + ext) if f.stem not in lines]
    if prune:
        for f in orphans:
            f.unlink()
            clips.pop(f.stem, None)
        print(f"pruned {len(orphans)} orphaned clip(s)")
    elif orphans:
        print(f"{len(orphans)} orphaned clip(s) left in place (--prune removes them)")

    clips = {k: v for k, v in clips.items() if k in lines}
    total = sum(v["b"] for v in clips.values())
    manifest_path.write_text(json.dumps({
        "backend": backend_key,
        "model": (tts.model if tts else old.get("model", model)),
        "voice": voice,
        "format": ext.lstrip("."),
        "clips": clips,
    }, indent=1, sort_keys=True) + "\n")

    print(f"{len(clips)} clips, {total / 1e6:.2f} MB in {out}")
    return 0 if len(clips) == len(lines) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", default="kitten", choices=sorted(BACKENDS))
    ap.add_argument("--model", default="", help="model id (backend default if unset)")
    ap.add_argument("--voice", default="", help="voice name (backend default if unset)")
    ap.add_argument("--no-clean", action="store_true",
                    help="skip the model's own number/abbreviation expansion")
    ap.add_argument("--out", default=str(OUT), type=pathlib.Path)
    ap.add_argument("--prune", action="store_true",
                    help="delete clips no line asks for any more")
    ap.add_argument("--limit", type=int, default=0,
                    help="render at most N missing clips (for a quick listen)")
    a = ap.parse_args()
    return render(a.backend, a.model, a.voice, not a.no_clean,
                  pathlib.Path(a.out), a.prune, a.limit)


if __name__ == "__main__":
    raise SystemExit(main())
