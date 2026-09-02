# Standard Operating Procedure (SOP) Template

**Domain**: [Domain Name]  
**Version**: 1.0  
**Last Updated**: [Date]  
**Owner**: [Role/Team]  
**Audience**: [Who should follow this]

---

## 1. Purpose

One-sentence statement of what this SOP achieves.

**Example**: Ensures video renders complete with production-tier quality and notify stakeholders of failures.

---

## 2. Scope

- **In Scope**: What this SOP covers
- **Out of Scope**: What it does not cover
- **Prerequisites**: What must be true before starting (tools, access, training, etc.)

---

## 3. Key Definitions & Abbreviations

| Term | Definition |
|------|-----------|
| GPU | Graphics Processing Unit (NVIDIA for rendering) |
| QA Tier | Production (1080p strict) or Draft (720p lenient) |
| Pre-flight | Validation checks before rendering starts |
| Transient | Temporary error that may succeed on retry |

---

## 4. Responsibilities & Roles

| Role | Responsibility | Escalation |
|------|-----------------|------------|
| Video Operator | Run nightly renders, monitor summary.txt | Manager if >2 failures |
| QA Lead | Define/adjust QA thresholds, review edge cases | CTO if accuracy <95% |
| Infrastructure | GPU provisioning, driver updates, disk management | VP Eng if hardware fails |

---

## 5. Pre-Execution Checklist

- [ ] Task/Job queue configured in `jobs/queue.json`
- [ ] Input files present and EXIF orientation correct (run `fix_exif.py` if needed)
- [ ] Disk space >20 GB available
- [ ] GPU not in use by other processes (check Task Manager)
- [ ] FFmpeg installed and on PATH
- [ ] Python venv activated with `requirements.txt` installed

---

## 6. Execution Steps

### Step 1: Pre-flight Validation (Dry-Run)
```bash
cd ai-projects/video-pipeline
python nightly_runner.py --queue jobs/queue.json --dry-run
```
**Expected output**: All checks PASS or WARN (not FAIL)  
**If FAIL**: Fix the issue in the "Recovery Actions" section, then re-run.

### Step 2: Run Nightly Render
```bash
python nightly_runner.py --queue jobs/queue.json
```
**Expected output**: `summary.txt` with all jobs PASS  
**Time estimate**: 1 job = ~15 min (HeyGen) or ~45 min (Wan2GP)  
**Monitoring**: Check `nvidia-smi` in another terminal to see GPU utilization ramp up.

### Step 3: Review Reports
```bash
cat reports/$(date +%Y-%m-%d)/summary.txt
```
**Expected output**: `RESULT: X passed, 0 failed`  
**If failures**: Read the log tail and recovery actions, then proceed to **Post-Execution**.

---

## 7. Expected Outputs & Verification

| Output File | Format | What It Shows |
|-------------|--------|---------------|
| `summary.txt` | Plain text | Human-readable status, failures, and next steps |
| `summary.json` | JSON | Structured data for dashboards and monitoring |
| `{job}.log` | Plain text | Full command output and stderr |
| `{job}.qc.json` | JSON | QA gate results (PASS/WARN/FAIL per check) |

**Verification**: All jobs should have status `PASS` or `WARN` (never `FAIL`).

---

## 8. Troubleshooting & Recovery

### Scenario: "Pre-flight FAIL: GPU not idle"

**Root cause**: Another process is using the GPU.

**Recovery steps**:
1. Open Task Manager → Performance tab → GPU
2. Identify the process using >5% GPU
3. Right-click → End task
4. Wait 10 seconds, then re-run nightly_runner.py

**Prevention**: Disable auto-start processes that use GPU; schedule renders when workstation is quiet.

### Scenario: "Job TIMEOUT after 120 min"

**Root cause**: Render is too complex for the configured timeout.

**Recovery steps**:
1. Check the job config in `jobs/queue.json` → increase `timeout_min` to 180 (3 hours)
2. Or reduce resolution/frame count in the job's `cmd`
3. Re-run: `python nightly_runner.py --queue jobs/queue.json --max-jobs 1`

**Prevention**: Calibrate timeout per job type; HeyGen ~15 min, Wan2GP ~45 min at 1080p.

### Scenario: "Job FAIL_QC: sharpness below threshold"

**Root cause**: Input image is blurry or has low EXIF quality.

**Recovery steps**:
1. Inspect the input photo: does it look sharp in the original?
2. If blurry: replace with higher-quality original
3. If sharp: the model may be over-denoising; check qc_video.py → lower `SHARPNESS_MIN`
4. Re-run with fixed input

**Prevention**: Use high-quality originals (≥8MP, shot in good lighting).

---

## 9. Rollback & Reversal

**Scenario**: Render output is damaged or needs to be re-done.

**Rollback steps**:
1. Delete the output file: `rm reports/2026-09-02/job.mp4`
2. Delete the QC report: `rm reports/2026-09-02/job.qc.json`
3. Re-run: `python nightly_runner.py --queue jobs/queue.json --max-jobs 1`

**If entire day's output is bad**:
```bash
rm -rf reports/2026-09-02/
python nightly_runner.py --queue jobs/queue.json
```

**Post-rollback**: Verify new summary.txt shows all PASS.

---

## 10. Post-Execution Checklist

- [ ] All jobs in `summary.txt` show status PASS
- [ ] No recovery actions needed
- [ ] Output files are present in the expected locations
- [ ] Email sent to stakeholders with summary.txt content
- [ ] Day's reports archived (optional: upload to cloud backup)

---

## 11. Escalation & Support

| Issue | Escalation Path | Contact |
|-------|-----------------|---------|
| GPU driver crash | Reboot, if persists contact Infrastructure | [Slack: #infra-support] |
| Python venv broken | Reinstall via `requirements.txt`, if persists contact DevOps | [Email: devops@] |
| Render quality threshold questions | Review `qc_video.py`, escalate to QA Lead | [Slack: #qa] |
| Urgent render (outside nightly window) | Manual execution, escalate to Manager | [On-call: +1-XXX-XXXX] |

---

## 12. Change Log

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | 2026-09-02 | Initial SOP with nightly_runner.py | Video Team |
| 1.1 | [Future] | Add manual render override procedure | [TBD] |

---

## 13. Appendix: Command Reference

```bash
# Dry-run (pre-flight only, no rendering)
python nightly_runner.py --queue jobs/queue.json --dry-run

# Run with custom timeout (3 hours instead of default 2)
python nightly_runner.py --queue jobs/queue.json --timeout-min 180

# Run 2 jobs with 5-minute gap
python nightly_runner.py --queue jobs/queue.json --max-jobs 2 --cooldown-min 5

# Check for stale lock and force-clear (use with caution)
rm reports/.lock
python nightly_runner.py --queue jobs/queue.json

# View today's report
cat reports/$(date +%Y-%m-%d)/summary.txt

# View job-specific QC details
python -c "import json; print(json.dumps(json.load(open('reports/$(date +%Y-%m-%d)/job.qc.json')), indent=2))"
```

