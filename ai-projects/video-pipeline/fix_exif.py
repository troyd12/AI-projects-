#!/usr/bin/env python3
"""
fix_exif.py — make every source still upright in pixels, not just in an EXIF flag.

Wan2GP loads stills with a bare Image.open() and never calls exif_transpose, so a photo stored
landscape with Orientation=6 reaches the model rotated 90 degrees (15 of 21 photos in input\\ were
affected on 2026-08-29). ffmpeg honours the flag, PIL does not — so contact sheets look fine while
the renderer sees a sideways face.

    python fix_exif.py C:\\Wan2GP\\input            # report only
    python fix_exif.py C:\\Wan2GP\\input --write    # rewrite in place (originals copied to input\\_orig\\)

Also prints a sharpness score per photo (variance of Laplacian at 540 px wide — the HeyGen portrait
scored 698, the other variants 354-637) so the sharpest source can be chosen on numbers.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ORIENTATION_TAG = 0x0112
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
ANALYSIS_WIDTH = 540


def sharpness(img: Image.Image) -> float:
    g = img.convert("L")
    if g.width != ANALYSIS_WIDTH:
        g = g.resize((ANALYSIS_WIDTH, max(1, round(g.height * ANALYSIS_WIDTH / g.width))), Image.LANCZOS)
    a = np.asarray(g, dtype=np.float32)
    lap = -4 * a[1:-1, 1:-1] + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
    return float(lap.var())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    ap.add_argument("--write", action="store_true", help="rewrite rotated files upright, backing up originals to _orig/")
    ap.add_argument("--min-sharpness", type=float, default=300.0, help="flag stills softer than this (default 300)")
    a = ap.parse_args(argv)

    folder = Path(a.folder)
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS and p.is_file())
    if not files:
        print(f"no images in {folder}")
        return 2
    backup = folder / "_orig"
    rotated = soft = 0
    print(f"{'file':<32} {'stored':>10} {'orient':>6} {'upright':>10} {'sharp':>7}  verdict")
    for p in files:
        with Image.open(p) as im:
            orient = im.getexif().get(ORIENTATION_TAG, 1)
            stored = f"{im.width}x{im.height}"
            up = ImageOps.exif_transpose(im)
            upright = f"{up.width}x{up.height}"
            sharp = sharpness(up)
            notes = []
            if orient != 1:
                rotated += 1
                notes.append(f"ROTATED (EXIF {orient})")
                if a.write:
                    backup.mkdir(exist_ok=True)
                    if not (backup / p.name).exists():
                        shutil.copy2(p, backup / p.name)
                    exif = up.getexif()
                    if ORIENTATION_TAG in exif:
                        del exif[ORIENTATION_TAG]
                    save_kwargs = dict(exif=exif.tobytes()) if p.suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff"} else {}
                    if p.suffix.lower() in {".jpg", ".jpeg"}:
                        save_kwargs["quality"] = 95
                    up.save(p, **save_kwargs)
                    notes[-1] += " -> fixed"
            if sharp < a.min_sharpness:
                soft += 1
                notes.append("soft")
            print(f"{p.name:<32} {stored:>10} {orient:>6} {upright:>10} {sharp:>7.0f}  {'; '.join(notes) or 'ok'}")
    print(f"\n{len(files)} files, {rotated} rotated{' (fixed)' if a.write and rotated else ''}, {soft} below sharpness {a.min_sharpness:.0f}")
    if rotated and not a.write:
        print("re-run with --write to fix in place")
    return 1 if (rotated and not a.write) else 0


if __name__ == "__main__":
    sys.exit(main())
