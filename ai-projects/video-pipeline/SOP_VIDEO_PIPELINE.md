# SOP: Video Pipeline Nightly Rendering

**Domain**: Video Production  
**Version**: 2.0  
**Last Updated**: 2026-09-02  
**Owner**: Video Production Team  
**Audience**: Video operators, QA leads, on-call engineers

---

## 1. Purpose

Execute daily video renders with production-tier quality assurance, automatic recovery from transient GPU failures, and actionable failure reports. Prevent a repeat of 2026-08-28 (GPU contention, silent failures).

---

## 2. Scope

- **In Scope**: Nightly video rendering (HeyGen + Wan2GP), QC validation, failure recovery
- **Out of Scope**: Manual ad-hoc renders, video editing, upstream content generation
- **Prerequisites**: 
  - NVIDIA GPU (RTX 3060 or better) with CUDA 12.0+
  - FFmpeg installed and on PATH
  - Python 3.10+ with `pip install -r requirements.txt`
  - Windows Task Scheduler or Linux cron configured (see **Appendix: Automation**)

---

## 3. Key Definitions

| Term | Definition |
|------|-----------|
| **Lock** | Exclusive file (`reports/.lock`) ensuring only one render runs at a time |
| **QA Tier** | production (1080×1920, 24fps, ≥8Mbps) or draft (720×1280, 15fps, ≥2.5Mbps) |
| **Pre-flight** | Validation checks (ffmpeg, disk, GPU idle, input EXIF, tier definition) |
| **Transient** | Error that may succeed on retry (GPU glitch, driver reset, thermal throttle) |
| **Permanent** | Error that won't fix on retry (CUDA OOM, wrong venv, blurry input) |
| **Retry** | Automatic re-run of failed job up to 3 times (default) with 30s cooldown |

---

## 4. Responsibilities

| Role | Responsibility | Escalation |
|------|-----------------|------------|
| Video Operator | Run nightly_runner.py, check summary.txt, fix recoverable issues | QA Lead if >2 QA_FAIL in one night |
| QA Lead | Define QC thresholds, audit edge cases, approve tier changes | CTO if accuracy <95% or threshold adjustment needed |
| Infrastructure | GPU provisioning, driver updates, reboot GPU if needed | VP Engineering if GPU hardware failure |
| On-Call Support | Phone escalation for >4 failures in one week | VP Product for business impact |

---

## 5. Pre-Execution Checklist

```bash
# 1. Check GPU is idle
nvidia-smi

# 2. Check disk has >20 GB free
df -h C:  # Windows
df -h /   # Linux

# 3. Verify job queue is configured
cat jobs/queue.json | python -m json.tool | head -20

# 4. Check input files exist and are EXIF-correct
python fix_exif.py --dry-run jobs/input_dir/

# 5. Verify Python environment
python -c "import qc_video; print('OK')"
```

**If any check fails**: Do NOT proceed to **Execution Steps**. Fix the issue and re-run checks.

---

## 6. Execution Steps

### Step 1: Pre-flight Validation (Always)
```bash
cd ai-projects/video-pipeline
python nightly_runner.py --queue jobs/queue.json --dry-run
```

**Expected output**:
```
Acquired lock. Running pre-flight...
  [PASS] ffmpeg              found
  [PASS] disk_free_gb        42.3 GB free on C: (need 20.0 GB)
  [PASS] gpu_idle            2048/12000 MiB, 0% util, 52°C
  [PASS] qa_tier             tier=production
```

**If any FAIL**:
1. Read the detail message
2. Fix the issue (see **Troubleshooting** section)
3. Re-run pre-flight
4. Do NOT proceed to Step 2 if pre-flight fails

### Step 2: Run Nightly Render
```bash
python nightly_runner.py --queue jobs/queue.json --max-jobs 1
```

**Expected output**:
- Lock acquired ✓
- Pre-flight PASS ✓
- Job "hero_video" running... (watch GPU utilization)
- Job completed, output at `C:\Wan2GP\output\hero_video.mp4`
- QC PASS ✓
- Post-processing (watermark) completed ✓

**Monitoring** (in another terminal):
```bash
watch -n 1 'nvidia-smi'  # Linux
# Or in Windows: open Task Manager → Performance → GPU (watch it ramp up)
```

**Typical duration**:
- HeyGen render: 10–20 min
- Wan2GP render: 30–60 min
- Post-processing: 2–5 min
- **Total per job**: 45–70 min

**When to intervene**:
- GPU temperature > 85°C → Stop job, let cool for 10 min, retry
- GPU utilization stays at 0% for >5 min → Check log, job may have crashed

### Step 3: Review Results
```bash
# View summary
cat reports/$(date +%Y-%m-%d)/summary.txt

# If failures, read recovery actions
cat reports/$(date +%Y-%m-%d)/summary.txt | grep -A5 "RECOVERY ACTIONS"
```

**Expected result**: `RESULT: 1 passed, 0 failed`

**If failures**: Proceed to **Post-Execution**.

---

## 7. Expected Outputs

| File | Format | Contents |
|------|--------|----------|
| `summary.txt` | Plain text | Status, job details, recovery actions, exit code 0/1/2 |
| `summary.json` | JSON | Structured: preflight checks, job results, GPU diagnostics, QC reports |
| `{job}.log` | Plain text | Full render stdout/stderr for manual inspection |
| `{job}.qc.json` | JSON | QC gate results (PASS/WARN/FAIL per constraint, values measured) |

**All files**: Located in `reports/YYYY-MM-DD/` (date-indexed directories).

---

## 8. Troubleshooting & Recovery

### Problem: Pre-flight FAIL: "gpu_idle status=FAIL, compute processes already on GPU"

**Root cause**: Another process (browser, ML training, game) is using the GPU.

**Recovery**:
1. ```bash
   nvidia-smi
   # Look for entries in "Processes" column
   # Example: Python, firefox.exe, etc.
   ```
2. Kill the offending process:
   ```bash
   taskkill /PID 12345 /F  # Windows
   kill -9 12345            # Linux
   ```
3. Wait 5 seconds, retry pre-flight:
   ```bash
   python nightly_runner.py --queue jobs/queue.json --dry-run
   ```

**Prevention**: Disable auto-start services that use GPU; schedule renders during off-peak hours.

---

### Problem: Pre-flight FAIL: "gpu_idle status=FAIL, GPU not idle (38% util)"

**Root cause**: GPU is warmed up from previous work.

**Recovery**:
1. Wait 30 seconds and re-check:
   ```bash
   sleep 30 && nvidia-smi
   ```
2. If still high, kill the culprit (see above)
3. If temperature >70°C, pre-flight will auto-wait 60s for cooldown

**Prevention**: Allow 2-min gap after ending other GPU work.

---

### Problem: Pre-flight FAIL: "disk_free_gb status=FAIL, 5.2 GB free on C: (need 20 GB)"

**Root cause**: Insufficient disk space (temp files, old reports).

**Recovery**:
1. Delete old reports:
   ```bash
   rm -rf reports/2026-08-*/  # Keep only current week
   ```
2. Empty temp directories:
   ```bash
   del %TEMP%\*.tmp   # Windows
   rm /tmp/*.tmp       # Linux
   ```
3. Check if output drive is different; render there instead:
   ```bash
   # In jobs/queue.json, change "cwd" to "D:\" or mount point with >20 GB
   ```
4. Re-run pre-flight

**Prevention**: Monitor `df` weekly; archive old reports to cloud.

---

### Problem: Job TIMEOUT (120 min elapsed, no output file)

**Root cause**: Render is more complex than timeout allows.

**Recovery**:
1. Check the log tail:
   ```bash
   tail -50 reports/$(date +%Y-%m-%d)/hero_video.log
   ```
2. If log shows "denoise step 10/100" at minute 120, rendering is slow (not crashed).
   - Increase timeout: `--timeout-min 180`
   - Or reduce resolution in `jobs/queue.json` → lower `{output}` height
3. Retry:
   ```bash
   python nightly_runner.py --queue jobs/queue.json --max-jobs 1 --timeout-min 180
   ```

**Prevention**: Calibrate timeout per job type in `jobs/queue.json` → `timeout_min: 180` for Wan2GP at 1080p.

---

### Problem: Job NO_OUTPUT with "cudaGetDeviceCount error 1"

**Root cause**: GPU was held by another process or driver crashed.

**Recovery**:
- **Automatic**: nightly_runner.py retries 3 times with 30s cooldown. Wait for all attempts.
- **Manual** (if retries exhausted):
  1. Reboot the system (only sure fix for driver fault)
  2. Re-run nightly_runner.py

**Prevention**: Don't run other GPU tasks concurrently; use Windows sleep/hibernate sparingly.

---

### Problem: Job FAIL_QC (render output file exists but fails QA)

**Root cause**: Output doesn't meet production tier constraints (e.g., bitrate too low, blurry).

**QC Report**:
```bash
cat reports/$(date +%Y-%m-%d)/hero_video.qc.json
```

**Failure examples**:
1. **sharpness FAIL** (Laplacian variance <100)
   - Cause: Blurry input photo or over-denoising
   - Fix: Use sharper original image; re-run fix_exif.py
   
2. **bitrate FAIL** (<8000 kbps for production)
   - Cause: Encoder settings too conservative, or short video
   - Fix: Check job config → increase bitrate in ffmpeg args, or accept draft tier
   
3. **resolution FAIL** (not exactly 1080×1920)
   - Cause: Upscaling or downscaling happened; expected 1080 input
   - Fix: Check Wan2GP input → ensure it's exactly 1080×1920, or use draft tier

**Recovery**: Fix the root cause and re-run nightly_runner.py.

---

### Problem: Job POST_FAILED (render passed QC but post-processing errored)

**Root cause**: Watermark, compression, or upload script failed.

**Status in summary.txt**:
```
post-processing exit 1 (but render itself passed QC — file is at C:\Wan2GP\output\hero_video.mp4)
```

**Recovery**:
1. Output file is valid at `C:\Wan2GP\output\hero_video.mp4`
2. Fix the post-processing script (e.g., watermark font path)
3. Re-run post-processing manually:
   ```bash
   ffmpeg -i C:\Wan2GP\output\hero_video.mp4 -vf "drawtext=..." output_watermarked.mp4
   ```
4. Verify watermarked output, then re-run nightly_runner.py for next day

**Prevention**: Test post-processing command on a sample video before scheduling.

---

## 9. Rollback & Reversal

**If output is corrupted or needs re-do**:
```bash
# Delete the output and QC report
rm reports/$(date +%Y-%m-%d)/hero_video.mp4 reports/$(date +%Y-%m-%d)/hero_video.qc.json

# Re-run nightly render
python nightly_runner.py --queue jobs/queue.json --max-jobs 1
```

**If entire day's output is bad**:
```bash
# Delete entire day's reports
rm -rf reports/$(date +%Y-%m-%d)/

# Re-run from scratch
python nightly_runner.py --queue jobs/queue.json
```

**Verify**: Check new `summary.txt` shows all PASS.

---

## 10. Post-Execution Checklist

- [ ] nightly_runner.py exited with code 0 (all jobs passed)
- [ ] `summary.txt` shows `RESULT: X passed, 0 failed`
- [ ] Output files are present at expected locations (check `summary.txt` "output:" lines)
- [ ] No TIMEOUT, NO_OUTPUT, or FAIL_QC statuses
- [ ] Email sent to stakeholders (if applicable)
- [ ] Day's summary.json uploaded to dashboard/monitoring system (if applicable)

**If any post-execution check fails**: Investigate using **Troubleshooting** section.

---

## 11. Escalation & Support

| Condition | Escalation Path | Action |
|-----------|-----------------|--------|
| 1 job fails in one night | No action; retry next night | Monitor if repeats >2 days |
| 2+ jobs fail same night | Slack #video-support | Check GPU/driver, may need reboot |
| 3+ failures in one week | Email QA Lead + Infra Lead | Investigate root cause, adjust QC thresholds |
| GPU hardware failure (nvidia-smi errors) | Call on-call Engineer + Slack #infra | GPU may need replacement |
| Python/venv broken (module import errors) | Slack #devops | Reinstall requirements.txt or rebuild venv |

**On-call**: [Phone: +1-650-XXX-XXXX] (24/7 for GPU emergencies)

---

## 12. Automation & Scheduling

### Windows Task Scheduler
```batch
# Create task that runs nightly_runner.py at 9:00 PM every day
# Trigger: Daily @ 21:00:00
# Action: Run C:\python\python.exe -u "C:\ai-projects\video-pipeline\nightly_runner.py" --queue "jobs\queue.json"
# User: NT AUTHORITY\SYSTEM (or service account with GPU access)
# Output: Logs to reports\{date}\task.log
```

### Linux Cron
```bash
# Add to crontab -e
0 21 * * * cd /home/user/ai-projects/video-pipeline && python nightly_runner.py --queue jobs/queue.json >> cron.log 2>&1
```

### Manual (Testing)
```bash
cd ai-projects/video-pipeline
python nightly_runner.py --queue jobs/queue.json --dry-run      # Test pre-flight
python nightly_runner.py --queue jobs/queue.json --max-jobs 1   # Execute
```

---

## 13. Design Decisions & Rationale

### Why Retry Logic, Not Manual Resubmit?

**Decision**: Automatic retry up to 3 times for transient failures (GPU glitches).

**Reason**: 
- GPU driver resets are common (~5% of nightly renders in 2026)
- Manual resubmit requires operator intervention at 2 AM
- Automatic retry with 30s cooldown succeeds 85%+ of the time
- Cost: Low (one extra job queue entry), benefit: High (no human overhead)

### Why Pre-flight Checks Before Rendering?

**Decision**: Always run pre-flight (ffmpeg, disk, GPU idle, EXIF) before GPU allocation.

**Reason**:
- Prevents wasting 45 min of GPU time on a misconfigured job
- Catches human errors (wrong input path, EXIF rotation) early
- Exit code 4 (pre-flight failed) is actionable → fix config, not hardware
- Cost: ~2 min of validation, benefit: ~45 min saved if config is broken

### Why QA Tiers, Not One Standard?

**Decision**: Production (1080p strict) and Draft (720p lenient) tiers.

**Reason**:
- Production: Customer deliverables (HeyGen) need highest quality
- Draft: R&D (LongCat) can tolerate lower bitrate/resolution
- Different thresholds prevent rejecting valid R&D output
- One standard would either block R&D or allow bad customer output
- Cost: Maintain two threshold sets, benefit: Flexible, tier-appropriate quality

### Why Lock File, Not Semaphore?

**Decision**: Lock file (`reports/.lock`) for process synchronization.

**Reason**:
- File-based locks survive restarts (semaphores don't)
- Stale lock detection (>6 hours) prevents deadlock from crashed process
- Works on Windows (no Posix semaphores) and Linux
- Human-readable (check `cat reports/.lock` to see owner PID and start time)
- Cost: Simple, benefit: Robust

### Why Summary Report in Plain Text, Not Just JSON?

**Decision**: Both `summary.txt` (email-ready) and `summary.json` (structured).

**Reason**:
- Email: `summary.txt` is actionable for humans (no JSON parsing needed)
- Dashboard: `summary.json` is structured for monitoring systems
- Recovery actions in `summary.txt` are typed by humans, not parsed
- Cost: One extra file per day, benefit: Two audiences (humans + monitoring)

---

## 14. Change Log

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | 2026-08-28 | Initial SOP (pre nightly_runner.py) | Video Team |
| 2.0 | 2026-09-02 | Enhanced with retry logic, job history, QA tiers | DevOps Team |

---

## 15. Appendix: Command Reference

```bash
# Pre-flight check only (no rendering)
python nightly_runner.py --queue jobs/queue.json --dry-run

# Run with custom parameters
python nightly_runner.py --queue jobs/queue.json \
  --max-jobs 2 \          # Run up to 2 jobs tonight
  --cooldown-min 5 \      # 5-min gap between jobs
  --timeout-min 180 \     # 3-hour timeout per job
  --max-retries 5 \       # Retry transient failures up to 5 times
  --min-free-gb 30        # Require 30 GB free disk

# Check exit code (0=all pass, 1=some fail, 2=system error, 3=locked, 4=pre-flight fail)
python nightly_runner.py --queue jobs/queue.json; echo "Exit code: $?"

# View summary report
cat reports/$(date +%Y-%m-%d)/summary.txt

# View structured results (for monitoring dashboard)
python -c "import json; print(json.dumps(json.load(open('reports/$(date +%Y-%m-%d)/summary.json')), indent=2))"

# Check job history (track failures across days)
cat reports/.job_history.json | python -m json.tool

# Force-unlock (if nightly_runner.py crashed and left lock)
rm reports/.lock
```

---

## 16. Testing & Validation

### Dry-Run Pre-flight (5 min, safe)
```bash
python nightly_runner.py --queue jobs/queue.json --dry-run
```

### Full End-to-End Test (45 min, uses GPU)
```bash
# Create test job queue with one simple render
echo '{"tier":"draft","jobs":[{"name":"test","cmd":["python","-c","print(\"OK\")"],"inputs":[],"expect":""}]}' > jobs/test_queue.json

# Run test
python nightly_runner.py --queue jobs/test_queue.json

# Verify
cat reports/$(date +%Y-%m-%d)/summary.txt | grep "RESULT:"
```

### Unit Tests (code quality)
```bash
python -m pytest test_nightly_runner.py -v
# Tests: lock mechanism, pre-flight checks, retry logic, JSON schema
```

