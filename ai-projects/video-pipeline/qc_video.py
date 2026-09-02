#!/usr/bin/env python3
"""
qc_video.py — quality gate for a rendered clip (LongCat/Wan2GP, MuseTalk, HeyGen, ffmpeg post).

    python qc_video.py CLIP.mp4                      # production tier, prints a table
    python qc_video.py CLIP.mp4 --tier draft
    python qc_video.py CLIP.mp4 --json report.json   # machine-readable report next to the table
    python qc_video.py CLIP.mp4 --min-sharpness 90   # override any single threshold

Exit code: 0 PASS, 1 FAIL, 2 could not analyse (missing file / no ffmpeg).
Needs: Python 3.10+, Pillow, numpy, ffmpeg (ffprobe optional) on PATH or via FFMPEG / FFPROBE env vars.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TIERS = {
    # production = what ships to TheScamFile / Fraud Squad. Native 9:16 1080p, nothing softer.
    "production": dict(width=1080, height=1920, exact_size=True, min_fps=24.0, min_bitrate_kbps=8000,
                       min_sharpness=100.0, max_bar_frac=0.01, min_duration_s=1.0,
                       require_audio=True, min_mean_volume_db=-35.0),
    # draft = local R&D renders (480x832 / 720x1280 LongCat output). Looser, still catches broken files.
    "draft": dict(width=720, height=1280, exact_size=False, min_fps=15.0, min_bitrate_kbps=2500,
                  min_sharpness=60.0, max_bar_frac=0.02, min_duration_s=0.5,
                  require_audio=False, min_mean_volume_db=-45.0),
}
ANALYSIS_WIDTH = 540   # frames are resized to this width before sharpness, so numbers compare across resolutions
BLACK_MEAN, WHITE_MEAN = 8.0, 247.0
FROZEN_DIFF = 0.3      # mean abs pixel diff (0-255) below which two sampled frames count as identical


# ---------------------------------------------------------------- binaries
def find_bin(name: str, env: str) -> str | None:
    p = os.environ.get(env) or shutil.which(name)
    if p:
        return p
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg  # optional fallback for machines without a system ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def _ratio(s: str | None) -> float | None:
    if not s:
        return None
    if "/" in s:
        a, b = s.split("/", 1)
        try:
            return float(a) / float(b) if float(b) else None
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------- probing
def probe(path: Path, ffprobe: str | None, ffmpeg: str) -> dict:
    info = dict(duration=None, width=None, height=None, fps=None, bitrate_kbps=None, vcodec=None,
                has_audio=False, acodec=None, sample_rate=None, channels=None, audio_duration=None, nb_frames=None)
    if ffprobe:
        out = subprocess.run([ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            j = json.loads(out.stdout)
            fmt = j.get("format", {})
            info["duration"] = float(fmt["duration"]) if fmt.get("duration") else None
            if fmt.get("bit_rate"):
                info["bitrate_kbps"] = int(fmt["bit_rate"]) // 1000
            for s in j.get("streams", []):
                if s.get("codec_type") == "video" and info["width"] is None:
                    info.update(width=s.get("width"), height=s.get("height"), vcodec=s.get("codec_name"),
                                fps=_ratio(s.get("avg_frame_rate")) or _ratio(s.get("r_frame_rate")))
                    if s.get("nb_frames", "").isdigit():
                        info["nb_frames"] = int(s["nb_frames"])
                    if s.get("duration") and not info["duration"]:
                        info["duration"] = float(s["duration"])
                elif s.get("codec_type") == "audio" and not info["has_audio"]:
                    info.update(has_audio=True, acodec=s.get("codec_name"), channels=s.get("channels"),
                                sample_rate=int(s["sample_rate"]) if s.get("sample_rate") else None,
                                audio_duration=float(s["duration"]) if s.get("duration") else None)
            return info
    # Fallback: parse `ffmpeg -i` (no ffprobe on the box).
    txt = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", txt)
    if m:
        info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    m = re.search(r"bitrate:\s*(\d+)\s*kb/s", txt)
    if m:
        info["bitrate_kbps"] = int(m[1])
    m = re.search(r"Video:\s*(\w+).*?(?<!\d)(\d{2,5})x(\d{2,5}).*?([\d.]+)\s*fps", txt)
    if m:
        info.update(vcodec=m[1], width=int(m[2]), height=int(m[3]), fps=float(m[4]))
    m = re.search(r"Audio:\s*(\w+).*?(\d+)\s*Hz,\s*([\w.]+)", txt)
    if m:
        info.update(has_audio=True, acodec=m[1], sample_rate=int(m[2]),
                    channels={"mono": 1, "stereo": 2}.get(m[3]))
    return info


def grab_frame(ffmpeg: str, path: Path, t: float) -> np.ndarray | None:
    out = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if out.returncode != 0 or not out.stdout:
        return None
    return np.asarray(Image.open(io.BytesIO(out.stdout)).convert("L"), dtype=np.float32)


def audio_stats(ffmpeg: str, path: Path) -> tuple[float | None, float | None]:
    txt = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m1 = re.search(r"mean_volume:\s*(-?[\d.]+) dB", txt)
    m2 = re.search(r"max_volume:\s*(-?[\d.]+) dB", txt)
    return (float(m1[1]) if m1 else None, float(m2[1]) if m2 else None)


# ---------------------------------------------------------------- frame metrics
def bar_bounds(g: np.ndarray) -> tuple[int, int, int, int]:
    """(left, right, top, bottom) pixel widths of uniform black/white bars hugging the frame edges."""
    def edge_runs(std: np.ndarray, mean: np.ndarray) -> tuple[int, int]:
        flat = (std < 4.0) & ((mean < 20) | (mean > 235))
        n = len(flat)
        a = 0
        while a < n and flat[a]:
            a += 1
        if a == n:            # whole frame flat: treat as fully barred
            return n, 0
        b = 0
        while b < n and flat[n - 1 - b]:
            b += 1
        return a, b
    l, r = edge_runs(g.std(axis=0), g.mean(axis=0))
    t, b = edge_runs(g.std(axis=1), g.mean(axis=1))
    return l, r, t, b


def to_analysis(g: np.ndarray) -> np.ndarray:
    h, w = g.shape
    if w == ANALYSIS_WIDTH:
        return g
    img = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
    img = img.resize((ANALYSIS_WIDTH, max(1, round(h * ANALYSIS_WIDTH / w))), Image.LANCZOS)
    return np.asarray(img, dtype=np.float32)


def sharpness(g: np.ndarray) -> float:
    """Variance of the Laplacian at ANALYSIS_WIDTH. Same measure used to rank the HeyGen stills (354-698)."""
    a = to_analysis(g)
    if a.shape[0] < 3 or a.shape[1] < 3:
        return 0.0
    lap = -4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    return float(lap.var())


# ---------------------------------------------------------------- the gate
def run_qc(path: Path, tier: str, samples: int, overrides: dict) -> dict:
    thr = dict(TIERS[tier])
    thr.update({k: v for k, v in overrides.items() if v is not None})
    ffmpeg = find_bin("ffmpeg", "FFMPEG")
    ffprobe = find_bin("ffprobe", "FFPROBE")
    checks: list[dict] = []

    def add(name, status, value=None, threshold=None, detail=""):
        checks.append(dict(name=name, status=status, value=value, threshold=threshold, detail=detail))

    if not ffmpeg:
        return dict(file=str(path), tier=tier, overall="ERROR", error="ffmpeg not found", checks=[])
    if not path.is_file() or path.stat().st_size == 0:
        return dict(file=str(path), tier=tier, overall="ERROR", error="file missing or empty", checks=[])

    info = probe(path, ffprobe, ffmpeg)
    dur, w, h, fps = info["duration"], info["width"], info["height"], info["fps"]
    if not (dur and w and h):
        return dict(file=str(path), tier=tier, overall="ERROR", error="could not read stream info", checks=[], probe=info)

    # -- container / stream
    add("duration_s", "PASS" if dur >= thr["min_duration_s"] else "FAIL", round(dur, 2), f">= {thr['min_duration_s']}")
    if thr["exact_size"]:
        ok = (w, h) == (thr["width"], thr["height"])
        add("resolution", "PASS" if ok else "FAIL", f"{w}x{h}", f"== {thr['width']}x{thr['height']}",
            "" if ok else "not native 9:16 1080p — re-export from HeyGen at 9:16 / render at final size; do not upscale")
    else:
        aspect_ok = abs((w / h) - (9 / 16)) <= 0.01
        size_ok = w >= thr["width"] and h >= thr["height"]
        add("resolution", "PASS" if (aspect_ok and size_ok) else "FAIL", f"{w}x{h}",
            f">= {thr['width']}x{thr['height']} and 9:16", "" if aspect_ok else "aspect is not 9:16")
    add("fps", "PASS" if (fps or 0) >= thr["min_fps"] else "FAIL", round(fps, 2) if fps else None, f">= {thr['min_fps']}")
    br = info["bitrate_kbps"]
    add("bitrate_kbps", "PASS" if (br or 0) >= thr["min_bitrate_kbps"] else "FAIL", br, f">= {thr['min_bitrate_kbps']}",
        "" if (br or 0) >= thr["min_bitrate_kbps"] else "encode with libx264 -crf 18 -preset slow (see README)")
    if info["nb_frames"] and fps:
        expected = dur * fps
        drift = abs(info["nb_frames"] - expected)
        add("frame_count", "PASS" if drift <= max(2, 0.02 * expected) else "WARN", info["nb_frames"], f"~{expected:.0f}",
            "" if drift <= 2 else "frame count does not match duration x fps — dropped or duplicated frames")

    # -- audio
    if info["has_audio"]:
        mean_db, max_db = audio_stats(ffmpeg, path)
        if mean_db is None:
            add("audio_level_db", "WARN", None, f">= {thr['min_mean_volume_db']}", "volumedetect gave no reading")
        else:
            add("audio_level_db", "PASS" if mean_db >= thr["min_mean_volume_db"] else "FAIL", mean_db,
                f">= {thr['min_mean_volume_db']}", "" if mean_db >= thr["min_mean_volume_db"] else "track is silent or near-silent")
            if max_db is not None and max_db > -0.1:
                add("audio_clipping", "WARN", max_db, "< -0.1 dB peak", "peaks touch 0 dBFS — normalise (loudnorm) before delivery")
        if info["audio_duration"] and abs(info["audio_duration"] - dur) > 0.15:
            add("audio_sync_length", "WARN", round(info["audio_duration"], 2), f"~{dur:.2f}", "audio and video lengths differ")
        if info["sample_rate"] and info["sample_rate"] < 44100:
            add("audio_sample_rate", "WARN", info["sample_rate"], ">= 44100", "low sample rate")
    else:
        add("audio_present", "FAIL" if thr["require_audio"] else "WARN", False, "audio stream required" if thr["require_audio"] else "optional")

    # -- sampled frames
    n = max(3, samples)
    times = np.linspace(min(0.1, dur / 4), max(dur - 0.1, dur * 0.75), n)
    sharp_vals, bar_fracs, black_at, white_at, frozen_pairs = [], [], [], [], 0
    prev = None
    for t in times:
        g = grab_frame(ffmpeg, path, float(t))
        if g is None:
            continue
        mean = float(g.mean())
        if mean < BLACK_MEAN:
            black_at.append(round(float(t), 2))
        elif mean > WHITE_MEAN:
            white_at.append(round(float(t), 2))
        l, r, tb, bb = bar_bounds(g)
        bar_fracs.append(max((l + r) / g.shape[1], (tb + bb) / g.shape[0]))
        content = g[tb:g.shape[0] - bb or None, l:g.shape[1] - r or None]
        if content.size and mean >= BLACK_MEAN and mean <= WHITE_MEAN:
            sharp_vals.append(sharpness(content))
        a = to_analysis(g)
        if prev is not None and prev.shape == a.shape and float(np.abs(a - prev).mean()) < FROZEN_DIFF:
            frozen_pairs += 1
        prev = a

    if not bar_fracs:
        add("frames_decoded", "FAIL", 0, f"{n} samples", "could not decode any frame")
    else:
        worst_bar = max(bar_fracs)
        add("pillarbox_letterbox", "PASS" if worst_bar <= thr["max_bar_frac"] else "FAIL", round(worst_bar, 3),
            f"<= {thr['max_bar_frac']}", "" if worst_bar <= thr["max_bar_frac"] else
            "uniform black/white bars at the edge — canvas changed shape (the HeyGen 604px-in-1920 problem); normalise to 9:16")
        if black_at:
            add("black_frames", "FAIL", black_at, "none", "black frames at these seconds")
        if white_at:
            add("white_frames", "FAIL", white_at, "none", "white frames at these seconds")
        if sharp_vals:
            med = float(np.median(sharp_vals))
            add("sharpness", "PASS" if med >= thr["min_sharpness"] else "FAIL", round(med, 1), f">= {thr['min_sharpness']}",
                "" if med >= thr["min_sharpness"] else "soft — upscaled or over-compressed; render at final size, calibrate threshold per README")
        if frozen_pairs >= 3:
            add("frozen_frames", "WARN", frozen_pairs, "< 3 identical consecutive samples", "long static stretch — stuck render or freeze frame")

    statuses = {c["status"] for c in checks}
    overall = "FAIL" if "FAIL" in statuses else ("WARN" if "WARN" in statuses else "PASS")
    return dict(file=str(path), tier=tier, overall=overall, probe=info, thresholds=thr, checks=checks)


def print_report(rep: dict) -> None:
    print(f"\nQC  {rep['file']}   tier={rep['tier']}   ->  {rep['overall']}")
    if rep.get("error"):
        print(f"  ERROR: {rep['error']}")
        return
    p = rep["probe"]
    print(f"  {p['width']}x{p['height']}  {p['fps'] and round(p['fps'], 2)} fps  {p['duration'] and round(p['duration'], 2)}s  "
          f"{p['bitrate_kbps']} kb/s  {p['vcodec']}  audio={'yes' if p['has_audio'] else 'no'}")
    for c in rep["checks"]:
        mark = {"PASS": "  ok ", "WARN": " warn", "FAIL": " FAIL"}[c["status"]]
        line = f"  [{mark}] {c['name']:<22} {str(c['value']):<18} {c['threshold'] or ''}"
        if c["detail"]:
            line += f"\n           -> {c['detail']}"
        print(line)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--tier", choices=TIERS, default="production")
    ap.add_argument("--samples", type=int, default=12, help="frames to sample across the clip (default 12)")
    ap.add_argument("--json", help="write the report to this path")
    for k in ("min_sharpness", "min_bitrate_kbps", "max_bar_frac", "min_fps", "min_duration_s", "min_mean_volume_db"):
        ap.add_argument("--" + k.replace("_", "-"), type=float, default=None)
    a = ap.parse_args(argv)
    overrides = {k: getattr(a, k) for k in ("min_sharpness", "min_bitrate_kbps", "max_bar_frac", "min_fps",
                                              "min_duration_s", "min_mean_volume_db")}
    rep = run_qc(Path(a.video), a.tier, a.samples, overrides)
    print_report(rep)
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=2, default=str))
    return {"PASS": 0, "WARN": 0, "FAIL": 1}.get(rep["overall"], 2)


if __name__ == "__main__":
    sys.exit(main())
