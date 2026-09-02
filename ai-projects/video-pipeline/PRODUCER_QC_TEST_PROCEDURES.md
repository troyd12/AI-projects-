# Producer QC v2 — Trial Run & Validation Procedures

**Goal**: Verify producer_qc.py works correctly before full production deployment.

---

## Phase 1: Unit Tests (Local Environment)

### 1.1 Test producer_qc.py Standalone

```bash
cd ai-projects/video-pipeline

# Test with a known video file (if available)
python producer_qc.py sample_video.mp4 --tier production --json report.json --html report.html

# Expected output:
# - JSON report with component scores
# - HTML report viewable in browser
# - Console summary with quality score and recommendations
```

**What to check:**
- ✓ No Python errors or exceptions
- ✓ JSON report contains: overall_score, overall_status, component_scores, recommendations
- ✓ HTML report renders correctly in browser
- ✓ Audio metrics (peak, average, LUFS) are populated if audio is present
- ✓ Recommendations are specific and actionable

### 1.2 Test with Different Video Tiers

```bash
# Production tier (stricter thresholds: ≥90 PASS, 80-90 WARN, <80 FAIL)
python producer_qc.py video.mp4 --tier production --json prod_report.json

# Draft tier (lenient thresholds: ≥80 PASS, 70-80 WARN, <70 FAIL)
python producer_qc.py video.mp4 --tier draft --json draft_report.json

# Compare JSON reports — production should have lower scores than draft
diff prod_report.json draft_report.json
```

**What to check:**
- ✓ Draft tier shows higher scores than production tier (same video)
- ✓ Status appropriately reflects tier (WARN in production might be PASS in draft)

---

## Phase 2: Integration Test (Nightly Runner)

### 2.1 Test nightly_runner.py with Producer QC

```bash
# Create test queue with 1-2 jobs
cat > test_queue.json << 'QUEUE'
{
  "jobs": [
    {
      "name": "test_avatar_001",
      "command": ["echo", "mock render complete"],
      "output": "/tmp/test_render.mp4",
      "tier": "production"
    }
  ]
}
QUEUE

# DRY RUN: pre-flight checks only, no actual render
python nightly_runner.py --queue test_queue.json --dry-run

# Expected output:
# - Pre-flight checks pass or warn appropriately
# - No actual rendering happens
# - summary.txt created with status
```

**What to check:**
- ✓ Pre-flight validation passes
- ✓ No errors from producer_qc path reference
- ✓ Reports directory created correctly

### 2.2 Test with Real Video File

```bash
# Use an actual HeyGen or Wan2GP render output
ACTUAL_VIDEO="/path/to/real/video.mp4"

# Create queue pointing to real video
cat > real_queue.json << 'QUEUE'
{
  "jobs": [
    {
      "name": "test_real_video",
      "command": ["cp", "$ACTUAL_VIDEO", "/tmp/test_real.mp4"],
      "output": "/tmp/test_real.mp4",
      "tier": "production"
    }
  ]
}
QUEUE

# Run with real video (will execute producer_qc)
python nightly_runner.py --queue real_queue.json --max-jobs 1

# Check output
ls -la reports/$(date +%Y-%m-%d)/
# Should contain: test_real_video.log, test_real_video.qc.json, test_real_video.producer_qc.json, test_real_video.producer_qc.html
```

**What to check:**
- ✓ All report files generated (.log, .qc.json, .producer_qc.json, .producer_qc.html)
- ✓ Producer QC JSON contains valid score (0-100) and status (PASS/WARN/FAIL)
- ✓ HTML report opens in browser and displays correctly
- ✓ Recommendations match the detected issues
- ✓ Audio metrics populated (if video has audio)

---

## Phase 3: Quality Threshold Calibration

This step requires real video samples to calibrate score thresholds.

### 3.1 Collect Sample Videos

Gather 5-10 representative videos:
- **2-3 "Good" videos**: Avatar renders that look/sound professional
- **2-3 "Acceptable" videos**: Renders with minor issues
- **1-2 "Bad" videos**: Renders with clear quality problems

### 3.2 Run Batch Analysis

```bash
mkdir -p calibration_samples
# Copy sample videos to calibration_samples/

for video in calibration_samples/*.mp4; do
  python producer_qc.py "$video" --tier production \
    --json "$(basename $video .mp4).producer_qc.json" \
    --html "$(basename $video .mp4).producer_qc.html"
done

# Collect all JSON reports
ls calibration_samples/*.producer_qc.json
```

### 3.3 Review Scores and Adjust Thresholds

**Current thresholds:**
```
Production tier:
  PASS:       ≥90
  WARN:     80-90
  FAIL:       <80

Draft tier:
  PASS:       ≥80
  WARN:     70-80
  FAIL:       <70
```

**Calibration questions:**
1. Do your "good" videos score ≥90?
2. Do your "bad" videos score <80?
3. Are the recommendations accurate?
4. Are audio metrics in the expected range?

**If thresholds need adjustment:**
Edit `generate_json_report()` in producer_qc.py:
```python
if tier == "production":
    pass_threshold, warn_threshold = 90, 80  # ← Adjust these
else:  # draft
    pass_threshold, warn_threshold = 80, 70  # ← Adjust these
```

---

## Phase 4: Production Rollout

Once calibration is complete:

### 4.1 Deploy to Windows

```powershell
# Copy files to production machine
Copy-Item -Path "producer_qc.py" -Destination "C:\Wan2GP\pipeline\"
Copy-Item -Path "nightly_runner.py" -Destination "C:\Wan2GP\pipeline\"

# Verify producer_qc.py can run
python C:\Wan2GP\pipeline\producer_qc.py --help
```

### 4.2 Update Task Scheduler

Ensure Task Scheduler job points to updated nightly_runner.py:
```
Program: C:\Python\python.exe
Arguments: C:\Wan2GP\pipeline\nightly_runner.py --queue C:\Wan2GP\jobs\queue.json
```

### 4.3 Monitor First Run

Watch the first nightly run with producer_qc:
- Check reports/YYYY-MM-DD/ directory
- Review HTML reports for quality
- Verify recommendations are appropriate
- Check summary.txt for any warnings

---

## Troubleshooting

### Producer QC Reports Not Generated

**Symptom**: producer_qc.json not in reports/ directory

**Causes & fixes:**
- PRODUCER_QC path wrong → Check nightly_runner.py line 41
- ffmpeg/ffprobe missing → Install ffmpeg: `choco install ffmpeg`
- Video file not readable → Check file permissions
- Timeout (video very long) → Increase timeout in nightly_runner.py line 455 (default 120s)

### Audio Metrics Empty

**Symptom**: "levels": null, "lufs": null in producer_qc.json

**Causes & fixes:**
- No audio track in video → Normal for some renders
- ffmpeg volumedetect filter not supported → Update ffmpeg
- Audio extraction timed out → Increase timeout

### HTML Report Doesn't Display

**Symptom**: HTML file opens but no styling or layout broken

**Fixes:**
- Open in different browser (Chrome/Firefox recommended)
- Disable ad blockers
- Check browser console for errors (F12)

### Scores Inconsistent with Manual Review

**Symptom**: producer_qc gives high score but video looks bad (or vice versa)

**Action**: Document the discrepancy:
```
Example: avatar_001.mp4
- Producer QC score: 85
- Manual assessment: Should be 70 (audio too quiet)
- Action needed: Adjust audio loudness detection thresholds
```

Then calibrate (Phase 3) with these examples.

---

## Success Criteria ✓

You can consider producer_qc v2 successfully deployed when:

1. ✓ Producer_qc.py runs without errors on all test videos
2. ✓ JSON and HTML reports generated for each job
3. ✓ Audio metrics (peak, average, LUFS) populate correctly
4. ✓ Scores align with manual quality assessment (within 10 points)
5. ✓ Recommendations are specific and actionable
6. ✓ Nightly runner integrates producer_qc without breaking
7. ✓ Quarantine logic works (scores <80 block delivery)
8. ✓ All reports visible in reports/YYYY-MM-DD/ directory
9. ✓ HTML reports are stakeholder-ready (professional appearance)
10. ✓ First week of production runs show no regressions

---

## Next Steps After Validation

Once producer_qc v2 is validated in production:
1. Monitor daily runs for 1 week
2. Collect feedback from video producers
3. Adjust thresholds based on real-world results
4. Document final calibrated thresholds in README
5. Begin Sprint 2: Enhanced audio clarity/intelligibility scoring
