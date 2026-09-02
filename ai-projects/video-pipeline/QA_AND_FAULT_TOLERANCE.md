# Quality Assurance & Fault Tolerance — Video Pipeline

## Overview

The video pipeline (`nightly_runner.py`) implements production-grade reliability with three layers:
1. **Pre-flight validation** — catches errors before GPU allocation
2. **Quality assurance gates** — ensures output meets production or draft tier requirements
3. **Fault tolerance** — automatic retry with intelligent recovery for transient failures

---

## Quality Assurance (QA) Tiers

Every render output passes a QC gate defined by its tier. See `qc_video.py` for full specifications.

### Production Tier
- **Resolution**: exactly 1080×1920 (no upscaling/downscaling)
- **Frame rate**: ≥24 fps
- **Bitrate**: ≥8000 kbps
- **Artifacts**: ≤1% pillarbox/letterbox
- **Sharpness**: Laplacian variance ≥100 (not blurry)
- **Content**: no black/white/frozen frames, no repeated frames
- **Audio**: required, ≥-35 dB

**Use for**: Customer deliverables, production HeyGen exports.

### Draft Tier
- **Resolution**: ≥720×1280
- **Frame rate**: ≥15 fps
- **Bitrate**: ≥2500 kbps
- **Artifacts**: ≤5% pillarbox/letterbox
- **Content**: no hard failures (black frames OK if brief)
- **Audio**: optional

**Use for**: R&D, internal testing, LongCat pipeline.

### QC Process
1. Render completes → output file created
2. If output exists and is >0 bytes:
   - Run `qc_video.py` with tier specification
   - Check all constraints
   - Generate `{job}.qc.json` report
3. Post-processing runs **only if QC passes**
4. If QC fails: mark as `FAIL_QC`, no post-processing, file preserved for manual inspection

---

## Pre-Flight Validation

Before any job runs, these checks are performed:

### Check: `ffmpeg`
- **Why**: Required for quality assurance (frame analysis) and post-processing
- **Failure**: FAIL — no render will start
- **Recovery**: Install FFmpeg and add to PATH, or set `FFMPEG` environment variable

### Check: `disk_free_gb`
- **Why**: Renders require temporary working space; default is 20 GB minimum
- **Failure**: FAIL — aborts before touching GPU
- **Recovery**: Delete old reports, clear temp directories, or increase `--min-free-gb`

### Check: `gpu_idle`
- **Why**: GPU contention caused the 2026-08-28 outage (4 renders launched simultaneously)
- **Details returned**:
  - `memory_used_mb` / `memory_total_mb` (idle = <25% used)
  - `utilization_pct` (idle = <15%)
  - `temperature_c` (warm = >70°C, cold = <50°C)
  - `compute_apps` (list of PIDs using the GPU)
- **Failure modes**:
  - `FAIL`: Another process owns the GPU or utilization is >15%
  - `WARN`: GPU is idle but warm (>70°C) — first job will wait 60s for cooldown
- **Recovery**:
  - Check `nvidia-smi` to identify competing processes
  - Kill task via Task Manager
  - Reboot if driver is unresponsive

### Check: Input File Integrity
- **Images**: EXIF orientation must be 1 (upright) or absent
- **Why**: Rotated photos (EXIF 3, 6, 8) are passed to Wan2GP as-is but should be upright-first
- **Failure**: FAIL — rotated image detected
- **Recovery**: Run `fix_exif.py --write` to reorient and backup originals to `_orig/`

### Check: QA Tier
- **Informational**: Logs which tier (production/draft) is configured
- **Why**: Different requirements apply; production is stricter (1080p, 24fps, ≥8Mbps)

---

## Fault Tolerance & Retry Logic

### Transient vs. Permanent Failures

Each known failure signature is classified:

| Signature | Classification | Explanation | Recovery |
|-----------|-----------------|-------------|----------|
| `cudaGetDeviceCount` | **TRANSIENT** | GPU held by another process or driver glitch | Retry after 30s cooldown; check Task Manager; reboot if needed |
| `CUDA out of memory` | **PERMANENT** | Not enough VRAM for this render config | Lower resolution/frame rate; enable model offload; upgrade GPU |
| `Denoising` | **TRANSIENT** | Died mid-denoise, no traceback | Usually driver reset or thermal throttle; disable sleep; check Event Viewer |
| `No module named` | **PERMANENT** | Wrong Python venv or missing package | Activate correct venv; `pip install -r requirements.txt` |
| `timeout` | **TRANSIENT** | Exceeded `--timeout-min` (default 120) | Increase timeout; reduce resolution; split into smaller jobs |

### Retry Behavior

```
Attempt 1: Run job
  ├─ Success → PASS, no retry
  ├─ Timeout → Check if transient → Sleep 30s → Attempt 2
  ├─ No output + transient signature → Sleep 30s → Attempt 2
  └─ No output + permanent signature → FAIL, skip remaining attempts

Attempt 2: Repeat above (cumulative fail time = 30s cooldown + render time)
Attempt 3: Repeat above

All attempts exhausted → Mark as FAIL or EXHAUSTED_RETRIES
```

### Job History Tracking

`reports/.job_history.json` tracks each job:

```json
{
  "job_name": {
    "date": "2026-09-02",
    "attempts_today": 2,
    "last_status": "PASS"
  }
}
```

This prevents **thrashing** — re-running the same job 20 times in one night when the root cause is a misconfigured input. After 3 attempts (default), the job is marked failed and human intervention is required.

### Temperature Throttling

- If GPU temperature > 70°C at pre-flight: wait 60s for cooldown
- If GPU temperature > 80°C during execution: (logged but not stopped; driver handles throttle)
- Rationale: Thermal throttle reduces performance 10–50% but is not an error — just slow

---

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | All jobs PASS (or no jobs ran) | Success; check reports for warnings |
| `1` | One or more jobs failed | Investigate summary.txt → recovery actions |
| `2` | Unrecoverable system fault | Fix (reboot, reinstall ffmpeg, free disk space) |
| `3` | Another run holds the lock | Wait for that run to complete, or force-unlock if >6 hours old |
| `4` | Pre-flight validation failed | Apply fixes (free disk, kill GPU jobs, rotate images, install ffmpeg) |

---

## Reporting & Recovery Actions

### summary.txt (Email-Ready)

Example output:

```
NIGHTLY RENDER — 2026-09-02
Started: 2026-09-02T21:00:00
QA Tier: production (production=1080p 24fps ≥8Mbps strict, draft=720p 15fps ≥2.5Mbps)

PRE-FLIGHT VALIDATION
  [PASS] ffmpeg              found
  [PASS] disk_free_gb        42.3 GB free on C: (need 20.0 GB)
  [PASS] gpu_idle            2048/12000 MiB, 0% util, 52°C
  [PASS] qa_tier             tier=production (production=1080p strict, draft=720p lenient)

JOBS
  hero_video           PASS                    12.3 min
      output: C:\Wan2GP\output\hero_video.mp4
      qc   : PASS
  promo_video          TIMEOUT (attempt 2)      120.0 min
      status: exceeded 120.0 min (attempt 2)
      log (tail):
        [11:50:23] Finalizing...
        [11:50:45] Cleanup...

RESULT: 1 passed, 1 failed

RECOVERY ACTIONS
  promo_video: Increase --timeout-min, reduce resolution/frame count, or split into smaller jobs.
```

### summary.json (Dashboard)

Structured for programmatic consumption:

```json
{
  "day": "2026-09-02",
  "started": "2026-09-02T21:00:00",
  "qa_tier": "production",
  "preflight": {
    "checks": [...],
    "gpu_diagnostics": {...},
    "overall": "PASS"
  },
  "jobs": [
    {
      "name": "hero_video",
      "status": "PASS",
      "started": "2026-09-02T21:00:30",
      "minutes": 12.3,
      "output": "...",
      "qc": {"overall": "PASS", "fails": [], "warns": []},
      "attempts": 1
    },
    ...
  ]
}
```

---

## Configuration & Tuning

### Command-Line Arguments

```bash
# Run all jobs with default settings (1 job/night, 3-min cooldown, 120-min timeout)
python nightly_runner.py --queue jobs/queue.json

# Dry-run: pre-flight only, no render
python nightly_runner.py --queue jobs/queue.json --dry-run

# Advanced: 2 jobs/night, 5-min cooldown, 30 GB min disk, 8-hour stale lock timeout, 5 retries
python nightly_runner.py --queue jobs/queue.json \
  --max-jobs 2 \
  --cooldown-min 5 \
  --min-free-gb 30 \
  --stale-hours 8 \
  --max-retries 5
```

### Tuning Recommendations

**Slow renders (>120 min for 1080p)**:
```bash
--timeout-min 180  # allow up to 3 hours
```

**GPU with limited VRAM (<4 GB)**:
```bash
--max-jobs 1  # run one at a time, fully serialize
```

**Multiple renders per night**:
```bash
--max-jobs 3 --cooldown-min 5  # 3 jobs with 5-min pause between
```

**Aggressive retry for transient GPU errors**:
```bash
--max-retries 5  # retry up to 5 times per job
```

---

## Known Limits & Workarounds

### Limit: Post-processing Failures Don't Retry

**Status**: `POST_FAILED`
**Reason**: Render passed QC → file is valid. Post-processing (watermark, compression, etc.) is orthogonal.
**Workaround**: Check the output file is present → if post-processing failed, fix the post-processing command and re-run manually.

### Limit: No Email Integration in Runner

**Reason**: Keeps the runner stateless and testable.
**Workaround**: Scheduled task (Windows) or cron job (Linux) reads `reports/YYYY-MM-DD/summary.txt` and emails it.

### Limit: Timeout is Per-Job, Not Global

**Reason**: Allows different jobs to have different timeouts.
**Workaround**: Set `timeout_min` in `jobs/queue.json` per job, or use `--timeout-min` CLI arg (applies to all jobs without explicit timeout).

---

## Testing & Validation

### Dry-Run Pre-flight
```bash
python nightly_runner.py --queue jobs/queue.json --dry-run
```
Runs all checks but skips rendering. Use this to validate config before production.

### Synthetic Failure Test (in `nightly_runner.py` test suite)
```bash
cd ai-projects/video-pipeline
python -m pytest test_nightly_runner.py -v
```
Verifies:
- Lock mechanism (exclusive, stale detection)
- Pre-flight checks (all 5 checks pass individually)
- Retry logic (transient failures retry, permanent ones don't)
- QC integration (PASS/WARN/FAIL propagation)
- JSON schema validity (summary.json parseable)

---

## Support & Debugging

### "Another run holds the lock"

```bash
# Check who owns it
cat reports/.lock
# If >6 hours old (or process is dead), delete it
rm reports/.lock
# Retry
python nightly_runner.py --queue jobs/queue.json
```

### "GPU not idle" at pre-flight

```bash
# See what's using the GPU
nvidia-smi
# Kill the offender
taskkill /PID <pid> /F
# Or reboot (safest)
```

### "Pre-flight FAIL" for unknown reason

```bash
# Check the full pre-flight report in summary.txt
cat reports/2026-09-02/summary.txt
# Or JSON for structured details
cat reports/2026-09-02/summary.json | python -m json.tool
```

### "FAIL_QC" on a render you know is good

```bash
# Check the QC report
cat reports/2026-09-02/job.qc.json
# See which check failed (sharpness, bitrate, etc.)
# Adjust job config or qc_video.py thresholds
```

---

## Summary

| Layer | Mechanism | Assurance |
|-------|-----------|-----------|
| **Pre-flight** | 5 checks (ffmpeg, disk, GPU idle, input integrity, QA tier) | No wasted GPU time on bad config |
| **QA Gates** | Production/draft tier constraints | Every output validated against spec |
| **Fault Tolerance** | Transient vs. permanent classification + retry + cooldown + history | Automatic recovery from GPU glitches, driver resets, thermal throttle |
| **Reporting** | summary.txt (human) + summary.json (dashboard) + recovery actions | Next steps are actionable, no guessing |

