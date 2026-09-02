#!/usr/bin/env python3
"""
producer_qc.py — Movie Producer Quality Control

Production-grade video quality analysis: motion smoothness, brightness consistency,
color uniformity, audio levels, metadata validation. Scores 0-100 for approval.

    python producer_qc.py video.mp4 --tier production --json report.json --html report.html

Detects: motion stutter, brightness flicker, color shifts, audio peaks,
         compression artifacts, metadata compliance issues.

Report: JSON (structured) + HTML (visual) + text (email-ready)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import base64
from pathlib import Path

import cv2
import numpy as np
from subprocess import run, PIPE

HERE = Path(__file__).resolve().parent


# ---- VIDEO ANALYSIS ----
class VideoAnalyzer:
    """Analyze video frames for quality issues."""
    
    def __init__(self, video_path: str, sample_frames: int = 12):
        self.video_path = Path(video_path)
        self.sample_frames = sample_frames
        self.cap = cv2.VideoCapture(str(self.video_path))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_sec = self.frame_count / self.fps if self.fps else 0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def sample_frames_evenly(self) -> list[np.ndarray]:
        """Sample frames evenly across video duration."""
        frames = []
        if self.frame_count <= self.sample_frames:
            frame_indices = list(range(self.frame_count))
        else:
            frame_indices = np.linspace(0, self.frame_count - 1, self.sample_frames, dtype=int)
        
        for idx in frame_indices:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap.read()
            if ret:
                frames.append(frame)
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return frames
    
    def analyze_motion(self, frames: list[np.ndarray]) -> dict:
        """Detect motion smoothness (frame-to-frame differences)."""
        if len(frames) < 2:
            return {"status": "SKIP", "reason": "fewer than 2 frames"}
        
        diffs = []
        for i in range(1, len(frames)):
            gray1 = cv2.cvtColor(frames[i-1], cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray1, gray2)
            mean_diff = np.mean(diff)
            diffs.append(mean_diff)
        
        motion_variance = float(np.var(diffs))
        motion_score = max(0, 100 - motion_variance / 10)
        
        return {
            "status": "PASS" if motion_score > 75 else "WARN",
            "score": round(motion_score, 1),
            "variance": round(motion_variance, 2),
            "detail": "smooth motion" if motion_score > 75 else "potential stutter detected"
        }
    
    def analyze_brightness(self, frames: list[np.ndarray]) -> dict:
        """Detect brightness flicker/inconsistency."""
        if not frames:
            return {"status": "SKIP", "reason": "no frames"}
        
        brightness_values = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            brightness_values.append(brightness)
        
        brightness_std = float(np.std(brightness_values))
        brightness_score = max(0, 100 - brightness_std * 2)
        
        return {
            "status": "PASS" if brightness_score > 85 else "WARN",
            "score": round(brightness_score, 1),
            "std_dev": round(brightness_std, 2),
            "detail": "consistent brightness" if brightness_score > 85 else "flicker/dimming detected"
        }
    
    def analyze_color(self, frames: list[np.ndarray]) -> dict:
        """Detect color shifts using HSV saturation."""
        if not frames:
            return {"status": "SKIP", "reason": "no frames"}
        
        saturation_values = []
        for frame in frames:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            saturation = hsv[:, :, 1].mean()
            saturation_values.append(saturation)
        
        saturation_std = float(np.std(saturation_values))
        color_score = max(0, 100 - saturation_std)
        
        return {
            "status": "PASS" if color_score > 80 else "WARN",
            "score": round(color_score, 1),
            "saturation_std": round(saturation_std, 2),
            "detail": "uniform color" if color_score > 80 else "color shifts detected"
        }
    
    def analyze_artifacts(self, frames: list[np.ndarray]) -> dict:
        """Detect compression artifacts via Laplacian gradient."""
        if not frames:
            return {"status": "SKIP", "reason": "no frames"}
        
        artifact_energies = []
        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            energy = np.mean(np.abs(laplacian))
            artifact_energies.append(energy)
        
        mean_energy = float(np.mean(artifact_energies))
        artifact_quality = max(0, 100 - mean_energy / 5)
        
        return {
            "status": "PASS" if artifact_quality > 70 else "WARN",
            "score": round(artifact_quality, 1),
            "detail": "minimal artifacts" if artifact_quality > 70 else "compression artifacts possible"
        }
    
    def close(self):
        self.cap.release()


# ---- AUDIO ANALYSIS (ENHANCED) ----
class AudioAnalyzer:
    """Analyze audio track for quality issues with detailed metrics."""
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
    
    def extract_audio_levels(self) -> dict | None:
        """Extract detailed audio levels using ffmpeg."""
        try:
            # Use volumedetect filter to get peak and mean levels
            cmd = [
                "ffmpeg", "-i", str(self.video_path),
                "-af", "volumedetect",
                "-f", "null", "-"
            ]
            result = run(cmd, capture_output=True, text=True, timeout=60)
            
            output = result.stderr
            levels = {}
            
            # Parse volumedetect output
            for line in output.split('\n'):
                if 'mean_volume' in line:
                    # Format: "mean_volume: -XX.X dB"
                    parts = line.split(':')
                    if len(parts) > 1:
                        mean_db = float(parts[1].strip().split()[0])
                        levels['mean_level_db'] = round(mean_db, 1)
                
                if 'max_volume' in line:
                    # Format: "max_volume: -XX.X dB"
                    parts = line.split(':')
                    if len(parts) > 1:
                        max_db = float(parts[1].strip().split()[0])
                        levels['peak_level_db'] = round(max_db, 1)
            
            return levels if levels else None
        
        except Exception as e:
            return None
    
    def analyze_lufs(self) -> dict | None:
        """Calculate LUFS (Loudness Units relative to Full Scale)."""
        try:
            # Use ebur128 filter to calculate LUFS
            cmd = [
                "ffmpeg", "-i", str(self.video_path),
                "-af", "ebur128=peak=true",
                "-f", "null", "-"
            ]
            result = run(cmd, capture_output=True, text=True, timeout=60)
            
            output = result.stderr
            lufs_data = {}
            
            for line in output.split('\n'):
                if 'Integrated loudness' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        value = float(parts[1].strip().split()[0])
                        lufs_data['integrated_loudness'] = round(value, 1)
                
                if 'Loudness range' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        value = float(parts[1].strip().split()[0])
                        lufs_data['loudness_range'] = round(value, 1)
                
                if 'True peak' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        value = float(parts[1].strip().split()[0])
                        lufs_data['true_peak'] = round(value, 1)
            
            return lufs_data if lufs_data else None
        
        except Exception as e:
            return None
    
    def analyze(self) -> dict:
        """Extract and analyze audio from video."""
        try:
            # Get basic audio stream info
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=sample_rate,channels,codec_name,duration",
                "-of", "json",
                str(self.video_path)
            ]
            result = run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {"status": "WARN", "detail": "No audio track found"}
            
            data = json.loads(result.stdout)
            if not data.get("streams"):
                return {"status": "FAIL", "detail": "No audio stream found"}
            
            stream = data["streams"][0]
            sample_rate = int(stream.get("sample_rate", 0))
            channels = int(stream.get("channels", 0))
            codec = stream.get("codec_name", "unknown")
            
            audio_score = 100
            issues = []
            
            # Sample rate check
            if sample_rate < 44100:
                audio_score -= 20
                issues.append(f"sample rate too low ({sample_rate}Hz, need ≥44.1kHz)")
            elif sample_rate < 48000:
                audio_score -= 5
            
            # Channel check
            if channels < 1:
                audio_score -= 50
                issues.append("no audio channels")
            elif channels == 1:
                issues.append("mono audio detected (stereo recommended)")
                audio_score -= 10
            
            # Get detailed audio levels
            levels = self.extract_audio_levels()
            lufs = self.analyze_lufs()
            
            # Check audio levels
            if levels:
                peak_db = levels.get('peak_level_db', 0)
                mean_db = levels.get('mean_level_db', -30)
                
                # Peak should be ≥ -6dB (below clipping at 0dB)
                if peak_db > -1:
                    audio_score -= 15
                    issues.append(f"audio clipping detected (peak: {peak_db}dB)")
                elif peak_db < -24:
                    audio_score -= 10
                    issues.append(f"audio too quiet (peak: {peak_db}dB)")
                
                # Mean level should be -20dB to -18dB for conversational audio
                if mean_db < -30:
                    audio_score -= 15
                    issues.append(f"average level too low ({mean_db}dB)")
            
            if lufs:
                integrated = lufs.get('integrated_loudness', 0)
                # Standard target: -14 to -16 LUFS for streaming
                if integrated < -20:
                    audio_score -= 10
                    issues.append(f"LUFS too low ({integrated} LUFS, target -14 to -16)")
                elif integrated > -12:
                    audio_score -= 5
                    issues.append(f"LUFS too high ({integrated} LUFS, target -14 to -16)")
            
            result_dict = {
                "status": "PASS" if audio_score >= 80 else "WARN" if audio_score >= 60 else "FAIL",
                "score": audio_score,
                "sample_rate_hz": sample_rate,
                "channels": channels,
                "codec": codec,
                "issues": issues if issues else ["none"],
                "detail": "audio acceptable" if audio_score >= 80 else "audio issues detected",
                "levels": levels,
                "lufs": lufs,
            }
            
            return result_dict
        
        except Exception as e:
            return {"status": "WARN", "detail": f"Audio analysis error: {str(e)}"}


# ---- METADATA VALIDATION ----
class MetadataValidator:
    """Validate video metadata and compliance."""
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
    
    def analyze(self, expected_tier: str = "production") -> dict:
        """Validate video metadata."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_format", "-show_streams",
                "-of", "json",
                str(self.video_path)
            ]
            result = run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {"status": "FAIL", "detail": "Could not read metadata"}
            
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            
            checks = {}
            score = 100
            
            # Duration check
            duration = float(fmt.get("duration", 0))
            checks["duration"] = {
                "value": round(duration, 2),
                "unit": "seconds",
                "status": "PASS" if duration > 5 else "WARN"
            }
            if duration < 5:
                score -= 10
            
            # Codec check
            codec = video_stream.get("codec_name", "unknown")
            checks["codec"] = {
                "value": codec,
                "status": "PASS" if codec in ["h264", "h265", "hevc"] else "WARN"
            }
            if codec not in ["h264", "h265", "hevc"]:
                score -= 20
            
            # Resolution check
            width = video_stream.get("width")
            height = video_stream.get("height")
            checks["resolution"] = {
                "value": f"{width}x{height}",
                "status": "PASS"
            }
            
            # Frame rate check
            fps_str = video_stream.get("r_frame_rate", "0/1")
            try:
                fps_parts = fps_str.split("/")
                fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 0
                checks["fps"] = {
                    "value": round(fps, 2),
                    "status": "PASS" if fps >= 15 else "WARN"
                }
                if fps < 15:
                    score -= 20
            except:
                checks["fps"] = {"value": fps_str, "status": "WARN"}
                score -= 20
            
            return {
                "status": "PASS" if score >= 70 else "WARN",
                "score": score,
                "checks": checks,
                "detail": "metadata compliant" if score >= 70 else "metadata issues found"
            }
        
        except Exception as e:
            return {"status": "WARN", "detail": f"Metadata validation error: {e}"}


# ---- REPORTING ----
def generate_json_report(
    video_path: str,
    video_analysis: dict,
    audio_analysis: dict,
    metadata: dict,
    tier: str
) -> dict:
    """Generate comprehensive JSON quality report."""
    
    # Calculate overall score
    scores = [
        video_analysis.get("motion", {}).get("score", 0),
        video_analysis.get("brightness", {}).get("score", 0),
        video_analysis.get("color", {}).get("score", 0),
        video_analysis.get("artifacts", {}).get("score", 0),
        audio_analysis.get("score", 0),
        metadata.get("score", 0),
    ]
    overall_score = round(float(np.mean([s for s in scores if s > 0])), 1)
    
    # Determine status with tier-based thresholds
    if tier == "production":
        pass_threshold, warn_threshold = 90, 80
    else:  # draft
        pass_threshold, warn_threshold = 80, 70
    
    if overall_score >= pass_threshold:
        overall_status = "PASS"
    elif overall_score >= warn_threshold:
        overall_status = "WARN"
    else:
        overall_status = "FAIL"
    
    # Build recommendations
    recommendations = []
    if video_analysis.get("motion", {}).get("score", 100) < 75:
        recommendations.append("Motion stutter detected. Check source video or reduce denoise setting.")
    if video_analysis.get("brightness", {}).get("score", 100) < 85:
        recommendations.append("Brightness inconsistency detected. Check lighting or color grading.")
    if video_analysis.get("color", {}).get("score", 100) < 80:
        recommendations.append("Color shift detected. Verify color space and grading settings.")
    if video_analysis.get("artifacts", {}).get("score", 100) < 70:
        recommendations.append("Compression artifacts possible. Increase bitrate or check encoder.")
    if audio_analysis.get("score", 100) < 80:
        recommendations.append("Audio issues detected. Review audio track, levels, and channels.")
    if metadata.get("score", 100) < 70:
        recommendations.append("Metadata compliance issues. Verify codec, resolution, frame rate.")
    
    if not recommendations:
        recommendations = ["Video meets quality standards. Ready for delivery."]
    
    report = {
        "timestamp": dt.datetime.now().isoformat(),
        "video_path": str(video_path),
        "tier": tier,
        "overall_score": overall_score,
        "overall_status": overall_status,
        "component_scores": {
            "motion": video_analysis.get("motion", {}).get("score", 0),
            "brightness": video_analysis.get("brightness", {}).get("score", 0),
            "color": video_analysis.get("color", {}).get("score", 0),
            "artifacts": video_analysis.get("artifacts", {}).get("score", 0),
            "audio": audio_analysis.get("score", 0),
            "metadata": metadata.get("score", 0),
        },
        "video_analysis": video_analysis,
        "audio_analysis": audio_analysis,
        "metadata": metadata,
        "recommendations": recommendations,
    }
    
    return report


def generate_html_report(report: dict, output_file: str) -> None:
    """Generate HTML report for stakeholder review."""
    
    status_colors = {
        "PASS": "#22c55e",
        "WARN": "#f59e0b",
        "FAIL": "#ef4444",
        "SKIP": "#6b7280",
    }
    
    overall_status = report.get("overall_status", "UNKNOWN")
    overall_score = report.get("overall_score", 0)
    status_color = status_colors.get(overall_status, "#9ca3af")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Quality Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f3f4f6;
            color: #1f2937;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .score-box {{
            background: {status_color};
            color: white;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 30px;
            min-width: 200px;
            display: inline-block;
        }}
        .score-box .number {{
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .score-box .status {{
            font-size: 18px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            font-size: 20px;
            color: #1f2937;
            margin-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }}
        .component {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: #f9fafb;
            border-radius: 6px;
            margin-bottom: 10px;
        }}
        .component-name {{
            font-weight: 500;
            min-width: 150px;
        }}
        .component-score {{
            font-size: 18px;
            font-weight: bold;
            min-width: 50px;
        }}
        .progress-bar {{
            flex: 1;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            margin: 0 15px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: #667eea;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .recommendation {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px 15px;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        .recommendation.critical {{
            background: #fee2e2;
            border-left-color: #ef4444;
        }}
        .recommendation.success {{
            background: #dcfce7;
            border-left-color: #22c55e;
        }}
        .metadata-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .metadata-table th {{
            background: #e5e7eb;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #d1d5db;
        }}
        .metadata-table td {{
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge.pass {{
            background: #dcfce7;
            color: #166534;
        }}
        .badge.warn {{
            background: #fef3c7;
            color: #92400e;
        }}
        .badge.fail {{
            background: #fee2e2;
            color: #991b1b;
        }}
        .footer {{
            background: #f3f4f6;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Video Quality Report</h1>
            <p>Professional Production QC Analysis</p>
            <div style="text-align: center; margin-top: 20px;">
                <div class="score-box">
                    <div class="number">{overall_score}</div>
                    <div class="status">{overall_status}</div>
                </div>
            </div>
        </div>
        
        <div class="content">
            <!-- Video Info -->
            <div class="section">
                <h2>Video Information</h2>
                <table class="metadata-table">
                    <tr>
                        <th>Property</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>File</td>
                        <td><code>{report.get('video_path', 'N/A')}</code></td>
                    </tr>
                    <tr>
                        <td>Tier</td>
                        <td><strong>{report.get('tier', 'N/A').upper()}</strong></td>
                    </tr>
                    <tr>
                        <td>Timestamp</td>
                        <td>{report.get('timestamp', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            
            <!-- Component Scores -->
            <div class="section">
                <h2>Quality Component Scores</h2>
"""
    
    for component, score in report.get("component_scores", {}).items():
        score = float(score) if score else 0
        percentage = min(100, max(0, score))
        title = component.replace("_", " ").title()
        badge_class = "pass" if score >= 80 else "warn" if score >= 60 else "fail"
        
        html += f"""
                <div class="component">
                    <span class="component-name">{title}</span>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {percentage}%"></div>
                    </div>
                    <span class="component-score">{score}/100</span>
                    <span class="badge {badge_class}">{'PASS' if score >= 80 else 'WARN' if score >= 60 else 'FAIL'}</span>
                </div>
"""
    
    html += """
            </div>
            
            <!-- Recommendations -->
            <div class="section">
                <h2>Recommendations</h2>
"""
    
    for rec in report.get("recommendations", []):
        if "Ready for delivery" in rec:
            rec_class = "success"
        elif "detected" in rec.lower() or "too" in rec.lower():
            rec_class = "critical"
        else:
            rec_class = ""
        
        html += f'                <div class="recommendation {rec_class}">{rec}</div>\n'
    
    html += """
            </div>
            
            <!-- Audio Details -->
            <div class="section">
                <h2>Audio Analysis</h2>
"""
    
    audio = report.get("audio_analysis", {})
    if audio.get("levels"):
        levels = audio["levels"]
        html += f"""
                <table class="metadata-table">
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Peak Level</td><td>{levels.get('peak_level_db', 'N/A')} dB</td></tr>
                    <tr><td>Average Level</td><td>{levels.get('mean_level_db', 'N/A')} dB</td></tr>
                </table>
"""
    
    if audio.get("lufs"):
        lufs = audio["lufs"]
        html += f"""
                <table class="metadata-table" style="margin-top: 15px;">
                    <tr><th>Metric</th><th>Value</th><th>Target</th></tr>
                    <tr><td>Integrated Loudness</td><td>{lufs.get('integrated_loudness', 'N/A')} LUFS</td><td>-14 to -16 LUFS</td></tr>
                    <tr><td>Loudness Range</td><td>{lufs.get('loudness_range', 'N/A')} LU</td><td>Flexible</td></tr>
                    <tr><td>True Peak</td><td>{lufs.get('true_peak', 'N/A')} dB</td><td>&lt; -1 dB</td></tr>
                </table>
"""
    
    html += """
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Producer QC v2 | Movie Production Quality Control System</p>
            <p>For issues or questions, contact the production team.</p>
        </div>
    </div>
</body>
</html>
"""
    
    Path(output_file).write_text(html)


# ---- MAIN ----
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("video", help="Path to video file")
    ap.add_argument("--tier", default="production", choices=["production", "draft"])
    ap.add_argument("--json", help="Output JSON report to this file")
    ap.add_argument("--html", help="Output HTML report to this file")
    a = ap.parse_args(argv)
    
    video_path = Path(a.video)
    if not video_path.exists():
        print(f"ERROR: {video_path} not found", file=sys.stderr)
        return 1
    
    print(f"Analyzing {video_path.name}...")
    
    # Video analysis
    print("  Analyzing video frames...")
    va = VideoAnalyzer(str(video_path))
    frames = va.sample_frames_evenly()
    video_analysis = {
        "motion": va.analyze_motion(frames),
        "brightness": va.analyze_brightness(frames),
        "color": va.analyze_color(frames),
        "artifacts": va.analyze_artifacts(frames),
    }
    va.close()
    
    # Audio analysis
    print("  Analyzing audio (this may take a moment)...")
    aa = AudioAnalyzer(str(video_path))
    audio_analysis = aa.analyze()
    
    # Metadata validation
    print("  Validating metadata...")
    mv = MetadataValidator(str(video_path))
    metadata = mv.analyze(a.tier)
    
    # Generate report
    print("  Generating report...")
    report = generate_json_report(str(video_path), video_analysis, audio_analysis, metadata, a.tier)
    
    # Output JSON
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=2, default=str))
        print(f"✓ JSON report: {a.json}")
    
    # Output HTML
    if a.html:
        generate_html_report(report, a.html)
        print(f"✓ HTML report: {a.html}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Quality Score: {report['overall_score']}/100 ({report['overall_status']})")
    print(f"{'='*60}")
    print("\nRecommendations:")
    for rec in report["recommendations"]:
        print(f"  • {rec}")
    
    return 0 if report["overall_status"] in ("PASS", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
