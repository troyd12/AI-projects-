# Video pipeline — audit, quality gate, nightly runbook

Scope: the TheScamFile / Fraud Squad avatar-video jobs on the Windows box (`C:\Wan2GP`) — LongCat-Video renders
via Wan2GP, MuseTalk lip-sync, HeyGen cloud renders, and the ffmpeg post-processing step. Audit date 2026-09-02,
evidence = the 2026-08-29 status emails ("Avatar video — what exists", "Avatar source samples", "Welcome video — aspect fixed").

These scripts run on the PC, next to the pipeline. Copy this folder to `C:\Wan2GP\pipeline\`.

| File | Job |
|------|-----|
| `qc_video.py` | The quality gate. Fails a clip that is not native 1080×1920, has bars, is soft, is under-bitrate, is silent, or has black/frozen frames. |
| `fix_exif.py` | Makes source stills upright in pixels (Wan2GP ignores the EXIF flag). Also scores sharpness per photo. |
| `nightly_runner.py` | One lock, one job at a time, pre-flight before the GPU, QC after, honest `summary.txt`. |
| `jobs/queue.example.json` | Job queue format. |
| `selftest.py` | Synthesises broken clips and proves the gate catches them (11 checks, ~40 s, no GPU). |

## 1. What went wrong (and what each script does about it)

| # | Failure observed | Root cause | Fix |
|---|------------------|-----------|-----|
| 1 | 4 jobs (demo2, demo3, v2_photo12, v3_voiceneo) died in seconds with `cudaGetDeviceCount() Error 1` | Four scheduled tasks launched within 3 minutes; the GPU was already held | `nightly_runner.py`: lock file + `--max-jobs 1`. Pre-flight refuses to start if `nvidia-smi` shows any compute process or >25 % VRAM in use |
| 2 | v1_photo13 loaded the model, reached `[4/8] Denoising` at 16m44s, then the log stops dead. No mp4 | Killed or crashed mid-denoise — driver reset, thermal, sleep, or Windows Update restart | Runner records the real cause from the log tail (`KNOWN_FAILURES`), not a downstream symptom. Disable sleep/Update restarts for the render window (§4) |
| 3 | You received a "watermark failed" email | The watermark step ran on a file that never existed; the error masked the render failure | Post-processing (`post`) runs **only** after QC PASS. Summary states `NO_OUTPUT` + why |
| 4 | 15 of 21 input photos reached the model rotated 90° | `wgp.py` loads with bare `Image.open()`; EXIF Orientation=6 ignored (ffmpeg honours it, PIL doesn't — so contact sheets looked fine) | `fix_exif.py --write` rewrites upright pixels and strips the flag. Pre-flight fails on any input still with orientation ≠ 1 |
| 5 | HeyGen "Welcome" export: 604 px of picture in white bars for 9 s, then full-width landscape, then bars again | Canvas changed shape inside one HeyGen project; export was not native 9:16 | `qc_video.py` `pillarbox_letterbox` check (fails at >1 % bar width). Export at 9:16 from HeyGen (like "Fraud Squad Intro_1080p", which is true 1080×1920) instead of fixing after |
| 6 | Vertical segments upscaled 1.79× (604→1080) to rescue #5 | Upscale = less real detail than native | `sharpness` check catches soft frames; production tier requires native 1080×1920 |
| 7 | No clip ever passed a definition of "done" | There was no definition | The **production** tier below is the definition. Nothing ships without `qc_video.py` → PASS |

## 2. The quality gate ("intensity" turned up)

`python qc_video.py CLIP.mp4` — production tier is the default. Every threshold is overridable (`--min-sharpness 90`).

| Check | Production (ships) | Draft (local R&D) |
|-------|-------------------|-------------------|
| Resolution | exactly **1080×1920** | ≥ 720×1280, 9:16 ±1 % |
| Frame rate | ≥ 24 fps (deliver 30) | ≥ 15 |
| Bitrate | ≥ **8 000 kb/s** | ≥ 2 500 |
| Bars (pillar/letterbox) | ≤ 1 % of frame | ≤ 2 % |
| Sharpness (Laplacian variance @540 px) | ≥ 100 | ≥ 60 |
| Black / white frames | none | none |
| Audio | required, mean ≥ −35 dB, peaks < 0 dBFS, length matches video | optional |
| Frozen stretch | warn at 3 identical samples | warn |

**Calibrate sharpness once against your best real export** — run `python qc_video.py "Fraud Squad Intro_1080p.mp4" --json ref.json`, note the
`sharpness` value, and set `min_sharpness` in `TIERS` to ~70 % of it. Synthetic test patterns score far higher than faces; the threshold must
come from your own footage, not from this file.

### Render / export settings that pass the gate

- **HeyGen (production path):** export **1080p, 9:16 (vertical)**, one canvas for the whole project. Never mix a landscape scene into a vertical
  project — that is what produced the bars. Keep captions off in HeyGen; burn your own later on the clean plate.
- **LongCat / Wan2GP (local path):** render at the largest size the 48-minute budget allows and **never upscale more than 1.25×**. 480×832 output
  cannot pass production (it's a 2.3× upscale); it is a draft-tier tool for testing prompts, stills and voice. Keep one job per night, model
  offloading on, and let the GPU cool 3 min between jobs.
- **MuseTalk:** feed it the native-resolution talking-head clip, not a downscaled proxy; its output inherits the input's softness.
- **Final encode (ffmpeg):** `-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -r 30 -c:a aac -b:a 192k -ar 48000 -movflags +faststart`
  → typically 8–14 Mb/s at 1080×1920. Normalise speech with `-af loudnorm=I=-16:TP=-1.5:LRA=11` for social delivery.
- **Source stills:** mouth closed, eyes open, face filling the frame, even light, sharpest available (the HeyGen portrait scored 698; the
  alternatives 354–637). `fix_exif.py` prints the score for every file in `input\`.

## 3. Local vs HeyGen for the nightly — the decision

Measured on 2026-08-29: local LongCat = **48 min per 2.76 s** at 480×832, $0, needs the GPU to itself, faulted the driver once.
A 30-second segment ≈ **2.9 hours** and still comes out at draft resolution. HeyGen already has the avatar, renders 1080p in minutes, has an API.

Recommendation: **HeyGen for anything that ships; local for R&D** (new prompts, stills, voices). Both go through the same `qc_video.py` gate.
The nightly runner supports either — a HeyGen job is just a `cmd` that calls their API and downloads the mp4 into `expect`.

## 4. Nightly runbook

1. Copy this folder to `C:\Wan2GP\pipeline\`. `pip install pillow numpy`. Confirm `ffmpeg -version` works in a fresh terminal.
2. `python pipeline\fix_exif.py input --write` once, and again whenever you add photos.
3. Write `pipeline\jobs\queue.json` from the example. One job per night is the default; add more with `--max-jobs`.
4. `python pipeline\nightly_runner.py --queue pipeline\jobs\queue.json --dry-run` — pre-flight must be all PASS.
5. Delete the four old scheduled tasks and create **one**:
   ```
   schtasks /Create /TN "ScamFile Nightly Render" /SC DAILY /ST 23:30 /RL HIGHEST ^
     /TR "py -3 C:\Wan2GP\pipeline\nightly_runner.py --queue C:\Wan2GP\pipeline\jobs\queue.json"
   ```
6. Power: `powercfg /change standby-timeout-ac 0` and pause Windows Update restarts for the render window, so nothing kills a job at step 4/8.
7. Morning: `pipeline\reports\<date>\summary.txt` is the email. It says PASS / NO_OUTPUT / FAIL_QC / TIMEOUT with the cause and log tail —
   never "watermark failed" for a file that was never made. A Claude Routine (or the local session) can email it verbatim.

## 5. Which model does what

- **Rendering and QC need no LLM.** `qc_video.py`, `fix_exif.py` and `nightly_runner.py` are deterministic Python; they run on the
  scheduled task at $0 in tokens.
- **Morning email** (read `summary.txt`, send it, flag failures): a Haiku-class routine is sufficient.
- **Debugging a failed night** (read the log tail, decide what to change): Sonnet-class.
- **Building or changing the pipeline itself** (this folder): a one-time cost; any current model works, and the self-test proves the result either way.
