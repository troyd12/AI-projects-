#!/usr/bin/env python3
"""
selftest.py — proves qc_video.py and fix_exif.py catch the failure modes seen on 2026-08-29.
Synthesises clips with ffmpeg (no GPU, ~30 s) and asserts the verdicts.

    python selftest.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_video  # noqa: E402
import fix_exif  # noqa: E402

FF = qc_video.find_bin("ffmpeg", "FFMPEG")
V = "-c:v libx264 -pix_fmt yuv420p -r 30".split()
A_SINE = "-f lavfi -i sine=frequency=220:sample_rate=48000".split()
A_NULL = "-f lavfi -i anullsrc=r=48000:cl=mono".split()


def make(out: Path, src: str, audio: list[str], extra: list[str], t: float = 3.0, vf: str | None = None, crf="18"):
    cmd = [FF, "-v", "error", "-y", "-f", "lavfi", "-i", src, *audio, "-t", str(t), *V, "-crf", crf, *extra]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest", str(out)]
    subprocess.run(cmd, check=True)


def expect(name: str, rep: dict, overall: str, must_fail: set[str] = frozenset()) -> bool:
    fails = {c["name"] for c in rep["checks"] if c["status"] == "FAIL"}
    ok = rep["overall"] == overall and must_fail <= fails
    print(f"  {'ok  ' if ok else 'BAD '} {name:<28} overall={rep['overall']:<5} fails={sorted(fails) or '-'}")
    if not ok:
        qc_video.print_report(rep)
    return ok


def main() -> int:
    if not FF:
        print("ffmpeg not found")
        return 2
    results = []
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        print("synthesising clips ...")
        make(d / "clean.mp4", "testsrc2=size=1080x1920:rate=30", A_SINE, ["-b:v", "10M", "-minrate", "10M", "-maxrate", "12M", "-bufsize", "20M"])
        make(d / "pillarbox.mp4", "testsrc2=size=604x1920:rate=30", A_SINE, ["-b:v", "10M", "-minrate", "10M", "-maxrate", "12M", "-bufsize", "20M"],
             vf="pad=1080:1920:(ow-iw)/2:0:white")
        make(d / "silent.mp4", "testsrc2=size=1080x1920:rate=30", A_NULL, ["-b:v", "10M", "-minrate", "10M", "-maxrate", "12M", "-bufsize", "20M"])
        make(d / "lowbitrate.mp4", "testsrc2=size=1080x1920:rate=30", A_SINE, ["-b:v", "400k", "-maxrate", "400k", "-bufsize", "800k"], crf="35")
        make(d / "black.mp4", "color=c=black:size=1080x1920:rate=30", A_SINE, ["-b:v", "10M", "-minrate", "10M", "-maxrate", "12M", "-bufsize", "20M"])
        make(d / "soft.mp4", "testsrc2=size=1080x1920:rate=30", A_SINE, ["-b:v", "10M", "-minrate", "10M", "-maxrate", "12M", "-bufsize", "20M"],
             vf="boxblur=12:2")
        make(d / "landscape.mp4", "testsrc2=size=1920x1080:rate=30", A_SINE, ["-b:v", "10M", "-minrate", "10M", "-maxrate", "12M", "-bufsize", "20M"])
        make(d / "draft480.mp4", "testsrc2=size=480x832:rate=16", A_SINE, ["-b:v", "3M"])

        print("qc_video.py, production tier:")
        qc = lambda f, tier="production": qc_video.run_qc(d / f, tier, 10, {})  # noqa: E731
        results.append(expect("clean 1080x1920", qc("clean.mp4"), "PASS"))
        results.append(expect("white pillarbox 604->1080", qc("pillarbox.mp4"), "FAIL", {"pillarbox_letterbox"}))
        results.append(expect("silent audio", qc("silent.mp4"), "FAIL", {"audio_level_db"}))
        results.append(expect("400 kb/s encode", qc("lowbitrate.mp4"), "FAIL", {"bitrate_kbps"}))
        results.append(expect("black frames", qc("black.mp4"), "FAIL", {"black_frames"}))
        results.append(expect("blurred (upscale-like)", qc("soft.mp4"), "FAIL", {"sharpness"}))
        results.append(expect("landscape 1920x1080", qc("landscape.mp4"), "FAIL", {"resolution"}))
        results.append(expect("480x832 in production", qc("draft480.mp4"), "FAIL", {"resolution"}))
        print("qc_video.py, draft tier:")
        results.append(expect("480x832 in draft (too small)", qc("draft480.mp4", "draft"), "FAIL", {"resolution"}))
        results.append(expect("clean in draft", qc("clean.mp4", "draft"), "PASS"))

        print("fix_exif.py:")
        img = Image.radial_gradient("L").resize((400, 300)).convert("RGB")
        exif = Image.Exif()
        exif[0x0112] = 6
        img.save(d / "sideways.jpg", exif=exif.tobytes(), quality=95)
        img.save(d / "fine.jpg", quality=95)
        rc_report = fix_exif.main([str(d)])
        rc_write = fix_exif.main([str(d), "--write"])
        with Image.open(d / "sideways.jpg") as fixed:
            upright = (fixed.width, fixed.height) == (300, 400) and fixed.getexif().get(0x0112, 1) == 1
        ok = rc_report == 1 and rc_write == 0 and upright and (d / "_orig" / "sideways.jpg").exists()
        print(f"  {'ok  ' if ok else 'BAD '} rotated still detected, rewritten upright 300x400, original backed up")
        results.append(ok)

    print(f"\n{sum(results)}/{len(results)} checks behaved as expected")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
