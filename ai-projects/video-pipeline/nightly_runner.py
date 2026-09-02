#!/usr/bin/env python3
"""
nightly_runner.py — one lock, one job at a time, pre-flight before the GPU, QC after, honest report.

Replaces the four separate scheduled tasks that launched inside three minutes of each other on
2026-08-28 (cudaGetDeviceCount error 1: the GPU was already taken) and the "watermark failed" email
that hid the fact that no file had been rendered at all.

    python nightly_runner.py --queue jobs\\queue.json
    python nightly_runner.py --queue jobs\\queue.json --dry-run      # pre-flight only, no render
    python nightly_runner.py --queue jobs\\queue.json --max-jobs 2 --cooldown-min 5

Writes reports\\YYYY-MM-DD\\{job}.log, {job}.qc.json, summary.txt, summary.json.
summary.txt is what the morning email should contain — verbatim.

Exit: 0 all jobs PASS, 1 something failed, 3 another run holds the lock, 4 pre-flight failed.
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

KNOWN_FAILURES = [
    ("cudaGetDeviceCount", "GPU was already held by another process (or the driver had faulted). Only one job may run at a time — check nothing else is using the GPU, reboot if nvidia-smi itself errors."),
    ("CUDA out of memory", "Out of VRAM. Lower resolution / frame count, or enable the model's offload options."),
    ("Denoising", "Died mid-denoise (no traceback). Usually a driver reset, thermal throttle, sleep/hibernate, or Windows Update restart. Disable sleep for the render window and check Event Viewer > System for nvlddmkm."),
    ("No module named", "Python environment broken — wrong venv on the scheduled task."),
]


# ---------------------------------------------------------------- lock
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
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
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


# ---------------------------------------------------------------- pre-flight
def gpu_state() -> tuple[str, str]:
    """('PASS'|'WARN'|'FAIL', detail) — requires nvidia-smi; WARN if it is not on PATH."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return "WARN", "nvidia-smi not found; GPU idle check skipped"
    q = subprocess.run([smi, "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
                        "--format=csv,noheader,nounits"], capture_output=True, text=True)
    if q.returncode != 0:
        return "FAIL", f"nvidia-smi failed: {q.stderr.strip()[:200]} — driver fault? reboot before rendering"
    used, total, util, temp = [float(x) for x in q.stdout.strip().splitlines()[0].split(",")]
    apps = subprocess.run([smi, "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip()
    detail = f"{used:.0f}/{total:.0f} MiB used, {util:.0f}% util, {temp:.0f}C"
    if apps:
        return "FAIL", f"{detail}; compute processes already on the GPU: {apps.replace(chr(10), ' | ')}"
    if used / total > 0.25 or util > 15:
        return "FAIL", f"{detail}; GPU not idle"
    if temp > 70:
        return "WARN", f"{detail}; GPU already warm — first job may throttle"
    return "PASS", detail


def image_orientation(p: Path) -> int | None:
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.getexif().get(0x0112, 1)
    except Exception:
        return None


def preflight(queue: dict, out_root: Path, min_free_gb: float) -> list[dict]:
    checks = []
    checks.append(dict(name="ffmpeg", status="PASS" if shutil.which("ffmpeg") or os.environ.get("FFMPEG") else "FAIL",
                       detail="needed for QC and post-processing"))
    free_gb = shutil.disk_usage(out_root).free / 1e9
    checks.append(dict(name="disk_free_gb", status="PASS" if free_gb >= min_free_gb else "FAIL",
                       detail=f"{free_gb:.1f} GB free on {out_root.drive or out_root} (need {min_free_gb:.0f})"))
    s, d = gpu_state()
    checks.append(dict(name="gpu_idle", status=s, detail=d))
    for job in queue["jobs"]:
        cwd = Path(job.get("cwd", "."))
        for inp in job.get("inputs", []):
            p = (cwd / inp)
            if not p.exists():
                checks.append(dict(name=f"input:{job['name']}", status="FAIL", detail=f"missing {p}"))
                continue
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
                o = image_orientation(p)
                if o not in (1, None):
                    checks.append(dict(name=f"input:{job['name']}", status="FAIL",
                                       detail=f"{p.name} has EXIF orientation {o}: run fix_exif.py --write first"))
    return checks


# ---------------------------------------------------------------- jobs
def tail(path: Path, n: int = 30) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def diagnose(log_tail: str) -> str:
    for needle, why in KNOWN_FAILURES:
        if needle in log_tail:
            return why
    return "no known signature — read the log tail below"


def run_job(job: dict, day_dir: Path, tier: str, dry_run: bool) -> dict:
    name = job["name"]
    cwd = Path(job.get("cwd", "."))
    log = day_dir / f"{name}.log"
    expect = job.get("expect")
    result = dict(name=name, status="SKIPPED", started=dt.datetime.now().isoformat(timespec="seconds"),
                  minutes=0.0, output=None, qc=None, cause="", log=str(log))
    if dry_run:
        return result
    before = {Path(p).resolve() for p in glob.glob(str(cwd / expect))} if expect else set()
    t0 = time.time()
    timeout = job.get("timeout_min", 120) * 60
    with open(log, "w", errors="replace") as lf:
        lf.write(f"# {name}  {result['started']}\n# cwd={cwd}\n# cmd={' '.join(map(str, job['cmd']))}\n\n")
        lf.flush()
        try:
            proc = subprocess.run(job["cmd"], cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = None
            lf.write(f"\n# TIMEOUT after {timeout/60:.0f} min — killed\n")
        except FileNotFoundError as e:
            rc = -1
            lf.write(f"\n# could not start: {e}\n")
    result["minutes"] = round((time.time() - t0) / 60, 1)

    new = []
    if expect:
        for p in glob.glob(str(cwd / expect)):
            rp = Path(p).resolve()
            if rp not in before and rp.stat().st_mtime >= t0 - 1 and rp.stat().st_size > 0:
                new.append(rp)
    if rc is None:
        result.update(status="TIMEOUT", cause=f"exceeded {timeout/60:.0f} min")
        return result
    if not new:
        lt = tail(log)
        result.update(status="NO_OUTPUT", cause=diagnose(lt) + (f" (exit code {rc})" if rc else ""), log_tail=lt)
        return result

    out = max(new, key=lambda p: p.stat().st_mtime)
    result["output"] = str(out)
    qc_json = day_dir / f"{name}.qc.json"
    qc = subprocess.run([sys.executable, str(QC), str(out), "--tier", tier, "--json", str(qc_json)],
                        capture_output=True, text=True)
    with open(log, "a", errors="replace") as lf:
        lf.write("\n# ---- QC ----\n" + qc.stdout + qc.stderr)
    try:
        rep = json.loads(qc_json.read_text())
        fails = [c["name"] for c in rep["checks"] if c["status"] == "FAIL"]
        warns = [c["name"] for c in rep["checks"] if c["status"] == "WARN"]
        result["qc"] = dict(overall=rep["overall"], fails=fails, warns=warns, report=str(qc_json))
        result["status"] = "PASS" if rep["overall"] in ("PASS", "WARN") else "FAIL_QC"
        if fails:
            result["cause"] = "QC failed: " + ", ".join(fails)
    except Exception as e:
        result.update(status="FAIL_QC", cause=f"QC could not run: {e}")
        return result

    if result["status"] == "PASS" and job.get("post"):
        post = [str(x).replace("{output}", str(out)) for x in job["post"]]
        with open(log, "a", errors="replace") as lf:
            lf.write(f"\n# ---- post: {' '.join(post)} ----\n")
            lf.flush()
            pr = subprocess.run(post, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT)
        if pr.returncode != 0:
            result.update(status="POST_FAILED", cause=f"post-processing exit {pr.returncode} (render itself passed QC)")
    return result


# ---------------------------------------------------------------- summary
def write_summary(day_dir: Path, pre: list[dict], results: list[dict], started: str) -> str:
    lines = [f"NIGHTLY RENDER — {day_dir.name}  (started {started})", ""]
    lines.append("PRE-FLIGHT")
    for c in pre:
        lines.append(f"  [{c['status']:<4}] {c['name']:<20} {c['detail']}")
    lines.append("")
    lines.append("JOBS")
    if not results:
        lines.append("  none ran (pre-flight failed or --dry-run)")
    for r in results:
        lines.append(f"  {r['name']:<20} {r['status']:<12} {r['minutes']:>6.1f} min  {r['output'] or '-'}")
        if r.get("cause"):
            lines.append(f"      why: {r['cause']}")
        if r.get("qc"):
            q = r["qc"]
            extra = ""
            if q["warns"]:
                extra = f"  warns: {', '.join(q['warns'])}"
            lines.append(f"      qc : {q['overall']}{extra}")
        if r.get("log_tail"):
            lines.append("      log tail:")
            lines += ["        " + l for l in r["log_tail"].splitlines()[-12:]]
    n_pass = sum(r["status"] == "PASS" for r in results)
    lines += ["", f"RESULT: {n_pass}/{len(results)} passed QC"]
    txt = "\n".join(lines) + "\n"
    (day_dir / "summary.txt").write_text(txt)
    (day_dir / "summary.json").write_text(json.dumps(dict(day=day_dir.name, started=started, preflight=pre, jobs=results), indent=2))
    return txt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--queue", required=True, help="jobs\\queue.json")
    ap.add_argument("--reports", default=str(HERE / "reports"))
    ap.add_argument("--max-jobs", type=int, default=1, help="jobs per night (default 1 — one job owns the GPU)")
    ap.add_argument("--cooldown-min", type=float, default=3.0, help="idle minutes between jobs")
    ap.add_argument("--min-free-gb", type=float, default=20.0)
    ap.add_argument("--stale-hours", type=float, default=6.0, help="a lock older than this with a dead owner is removed")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    queue = json.loads(Path(a.queue).read_text())
    tier = queue.get("tier", "production")
    reports = Path(a.reports)
    day_dir = reports / dt.date.today().isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now().isoformat(timespec="seconds")

    lock = reports / ".lock"
    if not acquire_lock(lock, a.stale_hours):
        (day_dir / "summary.txt").write_text(f"NIGHTLY RENDER — {day_dir.name}\nSKIPPED: another run holds {lock}\n")
        print(f"another run holds {lock}; exiting")
        return 3
    try:
        pre = preflight(queue, reports, a.min_free_gb)
        results: list[dict] = []
        if any(c["status"] == "FAIL" for c in pre):
            print(write_summary(day_dir, pre, results, started))
            return 4
        for i, job in enumerate(queue["jobs"][: a.max_jobs]):
            if i and not a.dry_run:
                time.sleep(a.cooldown_min * 60)
            results.append(run_job(job, day_dir, tier, a.dry_run))
        for job in queue["jobs"][a.max_jobs:]:
            results.append(dict(name=job["name"], status="QUEUED", minutes=0.0, output=None, qc=None,
                                cause=f"beyond --max-jobs {a.max_jobs}; runs another night", log=""))
        print(write_summary(day_dir, pre, results, started))
        ran = [r for r in results if r["status"] not in ("QUEUED", "SKIPPED")]
        return 0 if all(r["status"] == "PASS" for r in ran) else 1
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    sys.exit(main())
