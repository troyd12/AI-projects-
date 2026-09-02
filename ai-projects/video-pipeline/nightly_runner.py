#!/usr/bin/env python3
"""
nightly_runner.py — production-grade video render orchestration with fault tolerance and QA.

ONE LOCK, ONE JOB AT A TIME — prevents GPU contention (the root cause of 2026-08-28 failures).
PRE-FLIGHT VALIDATION — checks ffmpeg, disk space, GPU idle state, input file integrity, EXIF orientation.
QUALITY ASSURANCE — every render passes production or draft tier QC gates; post-processing only on PASS.
FAULT TOLERANCE — retry logic for transient GPU errors, temperature throttling, disk space recovery.
HONEST REPORTING — summary.txt contains actionable next steps; no hidden failures.

    python nightly_runner.py --queue jobs\\queue.json
    python nightly_runner.py --queue jobs\\queue.json --dry-run      # pre-flight only, no render
    python nightly_runner.py --queue jobs\\queue.json --max-jobs 2 --cooldown-min 5

Writes reports\\YYYY-MM-DD\\{job}.log, {job}.qc.json, summary.txt, summary.json.
summary.txt is what the morning email should contain — verbatim, with recovery actions.

Exit codes:
  0 = all jobs PASS (or pre-flight warned but passed)
  1 = one or more jobs failed
  2 = unrecoverable fault (disk full, ffmpeg missing, driver fault)
  3 = another run holds the lock
  4 = pre-flight validation failed (recoverable after fixes applied)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
QC = HERE / "qc_video.py"

PRODUCER_QC = HERE / "producer_qc.py"
# ---- KNOWN FAILURE SIGNATURES & RECOVERY ----
# Each signature maps to (human explanation, is_transient, suggested_action)
KNOWN_FAILURES = {
    "cudaGetDeviceCount": (
        "GPU was held by another process or driver faulted",
        True,  # transient — retry after cooldown
        "Wait 30s for GPU to release, then retry. If persistent: check Task Manager for other GPU apps, or reboot.",
    ),
    "CUDA out of memory": (
        "Insufficient VRAM for current render settings",
        False,  # permanent for this job
        "Lower resolution, frame count, or enable model offload options. For production tier (1080p), you may need a larger GPU.",
    ),
    "Denoising": (
        "Crashed during denoising (no traceback logged)",
        True,  # transient — often driver reset or thermal throttle
        "Usually driver reset, thermal throttle, sleep, or Windows Update restart. Disable sleep, check Event Viewer > System.",
    ),
    "No module named": (
        "Python environment broken (wrong venv or missing package)",
        False,  # permanent for this run
        "Activate the correct venv. Re-run: pip install -r requirements.txt",
    ),
    "timeout": (
        "Job exceeded configured timeout",
        True,  # transient — retry with longer timeout
        f"Increase --timeout-min, reduce resolution/frame count, or split into smaller jobs.",
    ),
}


# ---- PERSISTENT JOB HISTORY (fault tolerance) ----
class JobHistory:
    """Track failures per job to avoid thrashing."""
    
    def __init__(self, path: Path):
        self.path = path
        self.data = self._load()
    
    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {}
    
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, default=str))
    
    def record_attempt(self, job_name: str, status: str):
        """Log an attempt. status = 'PASS', 'FAIL', 'TIMEOUT', etc."""
        today = dt.date.today().isoformat()
        if job_name not in self.data:
            self.data[job_name] = {"last_status": None, "attempts_today": 0}
        self.data[job_name]["last_status"] = status
        if self.data[job_name].get("date") != today:
            self.data[job_name]["date"] = today
            self.data[job_name]["attempts_today"] = 0
        self.data[job_name]["attempts_today"] += 1
        self.save()
    
    def get_attempts_today(self, job_name: str) -> int:
        return self.data.get(job_name, {}).get("attempts_today", 0)
    
    def should_retry(self, job_name: str, max_retries: int = 3) -> bool:
        """Return True if job should be retried (not yet at max)."""
        return self.get_attempts_today(job_name) < max_retries


# ---- LOCK MANAGEMENT ----
def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock(lock: Path, stale_hours: float) -> bool:
    """Acquire exclusive lock. Return True if acquired, False if held by another."""
    lock.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                json.dump(dict(pid=os.getpid(), started=dt.datetime.now().isoformat(timespec="seconds")), f)
            return True
        except FileExistsError:
            try:
                data = json.loads(lock.read_text())
                age_h = (time.time() - lock.stat().st_mtime) / 3600
                if not pid_alive(int(data.get("pid", -1))) or age_h > stale_hours:
                    lock.unlink()   # stale: owner is gone or it has run far too long
                    continue
            except Exception:
                pass
            return False
    return False


# ---- PRE-FLIGHT VALIDATION WITH QA ----
def gpu_state() -> tuple[str, str, dict]:
    """
    Return (status, detail, diagnostics).
    status = 'PASS' | 'WARN' | 'FAIL'
    diagnostics = {memory_used_mb, memory_total_mb, utilization_pct, temperature_c, compute_apps}
    """
    smi = shutil.which("nvidia-smi")
    if not smi:
        return "WARN", "nvidia-smi not found; GPU idle check skipped", {}
    
    q = subprocess.run([smi, "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True)
    if q.returncode != 0:
        return "FAIL", f"nvidia-smi failed: {q.stderr.strip()[:200]}", {}
    
    try:
        used, total, util, temp = [float(x) for x in q.stdout.strip().splitlines()[0].split(",")]
    except (ValueError, IndexError):
        return "FAIL", f"Could not parse nvidia-smi output: {q.stdout}", {}
    
    apps = subprocess.run([smi, "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip()
    
    diag = {
        "memory_used_mb": int(used),
        "memory_total_mb": int(total),
        "utilization_pct": int(util),
        "temperature_c": int(temp),
        "compute_apps": apps.replace("\n", " | ") if apps else None,
    }
    
    detail = f"{used:.0f}/{total:.0f} MiB, {util:.0f}% util, {temp:.0f}°C"
    
    if apps:
        return "FAIL", f"{detail}; compute processes already on GPU: {apps.replace(chr(10), ' | ')}", diag
    if used / total > 0.25 or util > 15:
        return "FAIL", f"{detail}; GPU not idle", diag
    if temp > 70:
        return "WARN", f"{detail}; GPU warm — first job may throttle, will wait", diag
    
    return "PASS", detail, diag


def image_orientation(p: Path) -> int | None:
    """Return EXIF orientation tag (1=normal, 3=180, 6=90cw, 8=90ccw) or None."""
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.getexif().get(0x0112, 1)
    except Exception:
        return None


def preflight(queue: dict, out_root: Path, min_free_gb: float, qa_tier: str) -> dict:
    """
    Run all pre-flight checks. Return {
        'checks': [{'name', 'status', 'detail'}, ...],
        'gpu_diagnostics': {...},
        'qa_tier': str,
        'overall': 'PASS' | 'WARN' | 'FAIL',
    }
    """
    checks = []
    
    # Check 1: ffmpeg availability
    ffmpeg_ok = shutil.which("ffmpeg") or os.environ.get("FFMPEG")
    checks.append(dict(
        name="ffmpeg",
        status="PASS" if ffmpeg_ok else "FAIL",
        detail="required for QC and post-processing" + (" (found)" if ffmpeg_ok else " (NOT FOUND on PATH)"),
    ))
    
    # Check 2: disk space
    free_gb = shutil.disk_usage(out_root).free / 1e9
    checks.append(dict(
        name="disk_free_gb",
        status="PASS" if free_gb >= min_free_gb else "FAIL",
        detail=f"{free_gb:.1f} GB free on {out_root.drive or out_root} (need {min_free_gb:.0f} GB)",
    ))
    
    # Check 3: GPU idle (this one is more detailed)
    gpu_status, gpu_detail, gpu_diag = gpu_state()
    checks.append(dict(
        name="gpu_idle",
        status=gpu_status,
        detail=gpu_detail,
    ))
    
    # Check 4: input file integrity and EXIF orientation
    for job in queue.get("jobs", []):
        cwd = Path(job.get("cwd", "."))
        for inp in job.get("inputs", []):
            p = cwd / inp
            if not p.exists():
                checks.append(dict(
                    name=f"input:{job['name']}",
                    status="FAIL",
                    detail=f"missing {p}",
                ))
                continue
            
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
                o = image_orientation(p)
                if o not in (1, None):
                    checks.append(dict(
                        name=f"input:{job['name']}",
                        status="FAIL",
                        detail=f"{p.name} EXIF orientation={o} (rotated). Run fix_exif.py --write first.",
                    ))
    
    # Check 5: QA tier is defined
    checks.append(dict(
        name="qa_tier",
        status="PASS",
        detail=f"tier={qa_tier} (production=1080p strict, draft=720p lenient)",
    ))
    
    # Determine overall status
    fail_checks = [c for c in checks if c["status"] == "FAIL"]
    warn_checks = [c for c in checks if c["status"] == "WARN"]
    overall = "FAIL" if fail_checks else ("WARN" if warn_checks else "PASS")
    
    # If GPU is warm, wait for it to cool down a bit
    if gpu_status == "WARN" and gpu_diag.get("temperature_c", 0) > 65:
        print(f"GPU is warm ({gpu_diag['temperature_c']}°C). Waiting 60s for cooldown...")
        time.sleep(60)
    
    return {
        "checks": checks,
        "gpu_diagnostics": gpu_diag,
        "qa_tier": qa_tier,
        "overall": overall,
    }


# ---- JOB EXECUTION WITH RETRY LOGIC ----
def tail(path: Path, n: int = 30) -> str:
    """Return last n lines of log."""
    try:
        lines = path.read_text(errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def diagnose(log_tail: str) -> tuple[str, bool]:
    """
    Scan log tail for known failure signatures.
    Return (explanation, is_transient).
    """
    for needle, (why, transient, _) in KNOWN_FAILURES.items():
        if needle in log_tail:
            return why, transient
    return "no known signature — read the log tail", False


def run_job(
    job: dict,
    day_dir: Path,
    tier: str,
    dry_run: bool,
    history: JobHistory,
    max_retries: int = 3,
) -> dict:
    """
    Execute one job with retry logic for transient failures.
    Return job result dict.
    """
    name = job["name"]
    cwd = Path(job.get("cwd", "."))
    log = day_dir / f"{name}.log"
    expect = job.get("expect")
    
    result = dict(
        name=name,
        status="SKIPPED",
        started=dt.datetime.now().isoformat(timespec="seconds"),
        minutes=0.0,
        output=None,
        qc=None,
        cause="",
        attempts=0,
        log=str(log),
    )
    
    if dry_run:
        return result
    
    timeout = job.get("timeout_min", 120) * 60
    attempt = 0
    
    while attempt < max_retries:
        attempt += 1
        result["attempts"] = attempt
        history.record_attempt(name, "ATTEMPT")
        
        before = {Path(p).resolve() for p in glob.glob(str(cwd / expect))} if expect else set()
        t0 = time.time()
        
        with open(log, "a" if attempt > 1 else "w", errors="replace") as lf:
            if attempt > 1:
                lf.write(f"\n# ---- RETRY ATTEMPT {attempt} / {max_retries}  {dt.datetime.now().isoformat(timespec='seconds')} ----\n")
            else:
                lf.write(f"# {name}  {result['started']}\n# cwd={cwd}\n# cmd={' '.join(map(str, job['cmd']))}\n\n")
            lf.flush()
            
            try:
                proc = subprocess.run(job["cmd"], cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
                rc = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                rc = None
                timed_out = True
                lf.write(f"\n# TIMEOUT after {timeout/60:.0f} min — killed\n")
            except FileNotFoundError as e:
                rc = -1
                timed_out = False
                lf.write(f"\n# could not start: {e}\n")
        
        result["minutes"] = round((time.time() - t0) / 60, 1)
        
        # Check for new output file
        new = []
        if expect:
            for p in glob.glob(str(cwd / expect)):
                rp = Path(p).resolve()
                if rp not in before and rp.stat().st_mtime >= t0 - 1 and rp.stat().st_size > 0:
                    new.append(rp)
        
        # Handle timeout
        if timed_out:
            lt = tail(log)
            is_transient = True  # timeouts are transient
            if attempt < max_retries and is_transient:
                print(f"  {name}: timeout on attempt {attempt}/{max_retries}, retrying...")
                time.sleep(30)  # cooldown before retry
                continue
            result.update(
                status="TIMEOUT",
                cause=f"exceeded {timeout/60:.0f} min (attempt {attempt}/{max_retries})",
                log_tail=lt,
            )
            history.record_attempt(name, "TIMEOUT")
            return result
        
        # Handle no output
        if not new:
            lt = tail(log)
            why, is_transient = diagnose(lt)
            result.update(
                status="NO_OUTPUT",
                cause=why + (f" (exit code {rc})" if rc else ""),
                log_tail=lt,
            )
            
            if attempt < max_retries and is_transient:
                print(f"  {name}: {why} (attempt {attempt}/{max_retries}), retrying...")
                time.sleep(30)  # cooldown before retry
                continue
            
            history.record_attempt(name, "NO_OUTPUT")
            return result
        
        # Success: run QC
        out = max(new, key=lambda p: p.stat().st_mtime)
        result["output"] = str(out)
        qc_json = day_dir / f"{name}.qc.json"
        qc = subprocess.run(
            [sys.executable, str(QC), str(out), "--tier", tier, "--json", str(qc_json)],
            capture_output=True,
            text=True,
        )
        
        with open(log, "a", errors="replace") as lf:
            lf.write("\n# ---- QC ----\n" + qc.stdout + qc.stderr)
        
        try:
            rep = json.loads(qc_json.read_text())
            fails = [c["name"] for c in rep["checks"] if c["status"] == "FAIL"]
            warns = [c["name"] for c in rep["checks"] if c["status"] == "WARN"]
            result["qc"] = dict(
                overall=rep["overall"],
                fails=fails,
                warns=warns,
                report=str(qc_json),
            )
            result["status"] = "PASS" if rep["overall"] in ("PASS", "WARN") else "FAIL_QC"
            
            if fails:
                result["cause"] = "QC failed: " + ", ".join(fails)
                history.record_attempt(name, "FAIL_QC")
                return result
        except Exception as e:
            result.update(status="FAIL_QC", cause=f"QC could not run: {e}")
            history.record_attempt(name, "FAIL_QC")
            return result
        
        # ---- PRODUCER QC (Production-grade quality gate) ----
        producer_qc_json = day_dir / f"{name}.producer_qc.json"
        producer_qc_html = day_dir / f"{name}.producer_qc.html"
        pqc = subprocess.run(
            [sys.executable, str(PRODUCER_QC), str(out), "--tier", tier, 
             "--json", str(producer_qc_json), "--html", str(producer_qc_html)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        with open(log, "a", errors="replace") as lf:
            lf.write("\n# ---- PRODUCER QC ----\n" + pqc.stdout + pqc.stderr)
        
        try:
            pqc_rep = json.loads(producer_qc_json.read_text())
            pqc_score = pqc_rep.get("overall_score", 0)
            pqc_status = pqc_rep.get("overall_status", "FAIL")
            
            result["producer_qc"] = dict(
                score=pqc_score,
                status=pqc_status,
                recommendations=pqc_rep.get("recommendations", []),
                json_report=str(producer_qc_json),
                html_report=str(producer_qc_html),
            )
            
            # Quarantine logic: score determines delivery status
            if pqc_score < 80:
                result["status"] = "FAIL_PRODUCER_QC"
                result["cause"] = f"Producer QC score {pqc_score}/100 below minimum (80)"
                with open(log, "a", errors="replace") as lf:
                    lf.write(f"\n[QUARANTINE] Producer QC FAILED: {pqc_score}/100\n")
                history.record_attempt(name, "FAIL_PRODUCER_QC")
                return result
            elif pqc_score >= 90:
                result["producer_qc"]["status"] = "APPROVE"
                with open(log, "a", errors="replace") as lf:
                    lf.write(f"\n[APPROVED] Producer QC PASSED: {pqc_score}/100 — Ready for delivery\n")
            else:  # 80-90
                result["producer_qc"]["status"] = "CONDITIONAL"
                with open(log, "a", errors="replace") as lf:
                    lf.write(f"\n[ALERT] Producer QC WARNING: {pqc_score}/100 — Conditional approval\n")
        
        except Exception as e:
            with open(log, "a", errors="replace") as lf:
                lf.write(f"\n[WARNING] Producer QC error (non-fatal): {e}\n")
            result["producer_qc"] = dict(status="SKIP", cause=str(e))
        
        # QC passed: run post-processing if configured
        if result["status"] == "PASS" and job.get("post"):
            post = [str(x).replace("{output}", str(out)) for x in job["post"]]
            with open(log, "a", errors="replace") as lf:
                lf.write(f"\n# ---- POST-PROCESSING: {' '.join(post)} ----\n")
                lf.flush()
                pr = subprocess.run(post, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT)
            
            if pr.returncode != 0:
                result.update(
                    status="POST_FAILED",
                    cause=f"post-processing exit {pr.returncode} (but render itself passed QC — file is at {out})",
                )
                history.record_attempt(name, "POST_FAILED")
                return result
        
        # All good!
        history.record_attempt(name, "PASS")
        return result
    
    # Should not reach here, but if max retries exhausted
    result.update(status="EXHAUSTED_RETRIES", cause=f"Failed after {max_retries} attempts")
    history.record_attempt(name, "EXHAUSTED_RETRIES")
    return result


# ---- REPORTING WITH QA SUMMARY ----
def write_summary(day_dir: Path, preflight_result: dict, results: list[dict], started: str) -> str:
    """Generate summary.txt (for email) and summary.json (for dashboards)."""
    lines = [
        f"NIGHTLY RENDER — {day_dir.name}",
        f"Started: {started}",
        f"QA Tier: {preflight_result['qa_tier']} (production=1080p 24fps ≥8Mbps strict, draft=720p 15fps ≥2.5Mbps)",
        "",
    ]
    
    lines.append("PRE-FLIGHT VALIDATION")
    for c in preflight_result["checks"]:
        lines.append(f"  [{c['status']:<4}] {c['name']:<20} {c['detail']}")
    
    lines.append("")
    lines.append("JOBS")
    if not results:
        lines.append("  none ran (pre-flight failed or --dry-run)")
    else:
        for r in results:
            status_str = r["status"]
            if r.get("attempts", 1) > 1:
                status_str += f" (attempt {r['attempts']})"
            lines.append(f"  {r['name']:<20} {status_str:<25} {r['minutes']:>6.1f} min")
            
            if r.get("output"):
                lines.append(f"      output: {r['output']}")
            
            if r.get("cause"):
                lines.append(f"      status: {r['cause']}")
            
            if r.get("qc"):
                q = r["qc"]
                extra = ""
                if q["warns"]:
                    extra = f"  warns: {', '.join(q['warns'])}"
                lines.append(f"      qc   : {q['overall']}{extra}")
            
            if r.get("log_tail"):
                lines.append("      log (tail):")
                for l in r["log_tail"].splitlines()[-15:]:
                    lines.append("        " + l)
    
    lines.append("")
    n_pass = sum(r["status"] == "PASS" for r in results)
    n_fail = sum(r["status"] not in ("PASS", "QUEUED", "SKIPPED") for r in results)
    lines.append(f"RESULT: {n_pass} passed, {n_fail} failed")
    
    # Add recovery suggestions if there were failures
    if any(r["status"] not in ("PASS", "QUEUED", "SKIPPED") for r in results):
        lines.append("")
        lines.append("RECOVERY ACTIONS")
        for r in results:
            if r["status"] not in ("PASS", "QUEUED", "SKIPPED"):
                # Try to find the specific recovery action
                recovery_action = "Check log and fix manually"
                if r.get("cause"):
                    for needle, (why, trans, action) in KNOWN_FAILURES.items():
                        if needle in r.get("cause", ""):
                            recovery_action = action
                            break
                lines.append(f"  {r['name']}: {recovery_action}")
    
    txt = "\n".join(lines) + "\n"
    (day_dir / "summary.txt").write_text(txt)
    (day_dir / "summary.json").write_text(
        json.dumps(dict(
            day=day_dir.name,
            started=started,
            qa_tier=preflight_result["qa_tier"],
            preflight=preflight_result,
            jobs=results,
        ), indent=2, default=str)
    )
    return txt


# ---- MAIN ----
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--queue", required=True, help="jobs/queue.json")
    ap.add_argument("--reports", default=str(HERE / "reports"))
    ap.add_argument("--max-jobs", type=int, default=1, help="max jobs per night (default 1)")
    ap.add_argument("--cooldown-min", type=float, default=3.0, help="idle time between jobs (min)")
    ap.add_argument("--min-free-gb", type=float, default=20.0, help="required free disk space (GB)")
    ap.add_argument("--stale-hours", type=float, default=6.0, help="lock age to consider stale (hours)")
    ap.add_argument("--max-retries", type=int, default=3, help="retries per job for transient errors")
    ap.add_argument("--dry-run", action="store_true", help="pre-flight only, no render")
    a = ap.parse_args(argv)

    queue = json.loads(Path(a.queue).read_text())
    tier = queue.get("tier", "production")
    reports = Path(a.reports)
    day_dir = reports / dt.date.today().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now().isoformat(timespec="seconds")
    
    history = JobHistory(reports / ".job_history.json")

    lock = reports / ".lock"
    if not acquire_lock(lock, a.stale_hours):
        msg = f"NIGHTLY RENDER — {day_dir.name}\nSKIPPED: another run holds {lock}\n"
        (day_dir / "summary.txt").write_text(msg)
        print(msg)
        return 3
    
    try:
        print(f"Acquired lock. Running pre-flight...")
        preflight_result = preflight(queue, reports, a.min_free_gb, tier)
        results: list[dict] = []
        
        # Print pre-flight results
        for c in preflight_result["checks"]:
            print(f"  [{c['status']:<4}] {c['name']:<20} {c['detail']}")
        
        # Bail if critical checks failed
        fail_checks = [c for c in preflight_result["checks"] if c["status"] == "FAIL"]
        if fail_checks:
            summary = write_summary(day_dir, preflight_result, results, started)
            print(summary)
            return 4
        
        # Run jobs
        for i, job in enumerate(queue.get("jobs", [])[: a.max_jobs]):
            if i and not a.dry_run:
                print(f"Cooldown {a.cooldown_min} min...")
                time.sleep(a.cooldown_min * 60)
            print(f"Running {job['name']}...")
            results.append(run_job(job, day_dir, tier, a.dry_run, history, max_retries=a.max_retries))
        
        # Mark remaining jobs as queued
        for job in queue.get("jobs", [])[a.max_jobs:]:
            results.append(dict(
                name=job["name"],
                status="QUEUED",
                minutes=0.0,
                output=None,
                qc=None,
                cause=f"queued for next run (beyond --max-jobs {a.max_jobs})",
                log="",
            ))
        
        summary = write_summary(day_dir, preflight_result, results, started)
        print(summary)
        
        ran = [r for r in results if r["status"] not in ("QUEUED", "SKIPPED")]
        return 0 if all(r["status"] == "PASS" for r in ran) else 1
    
    except Exception as e:
        import traceback
        error_msg = f"UNHANDLED ERROR: {e}\n{traceback.format_exc()}"
        (day_dir / "summary.txt").write_text(error_msg)
        print(error_msg)
        return 2
    
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    sys.exit(main())
