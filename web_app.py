#!/usr/bin/env python
from __future__ import annotations

import subprocess
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory


PROJECT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = PROJECT_DIR / "outputs"
EVIDENCE_DIR = PROJECT_DIR / "evidence"
SCRIPT_PATH = PROJECT_DIR / "douyin_creator_tracker.py"

app = Flask(__name__)


class JobState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: subprocess.Popen[str] | None = None
        self.logs: list[str] = []
        self.started_at: str = ""
        self.finished_at: str = ""
        self.returncode: int | None = None
        self.command: list[str] = []
        self.out_file: str = ""
        self.evidence_dir: str = ""

    def reset(self) -> None:
        self.logs = []
        self.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.finished_at = ""
        self.returncode = None


JOB = JobState()


def build_command(form: dict[str, str]) -> tuple[list[str], str, str]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = form.get("out_path", "").strip() or f"outputs/web_run_{ts}.xlsx"
    evidence_dir = form.get("evidence_dir", "").strip() or f"evidence/web_run_{ts}"

    cmd = ["python", str(SCRIPT_PATH)]
    profile_url = form.get("profile_url", "").strip()
    profile_list = form.get("profile_list", "").strip()
    target_video_id = form.get("target_video_id", "").strip()
    cdp_url = form.get("cdp_url", "").strip() or "http://127.0.0.1:9222"
    retries = form.get("retries", "").strip() or "1"
    min_delay = form.get("min_delay", "").strip() or "3"
    max_delay = form.get("max_delay", "").strip() or "9"
    limit = form.get("limit", "").strip() or "5"
    max_tabs = form.get("max_tabs", "").strip() or "3"
    incremental_daily_max = form.get("incremental_daily_max", "").strip() or "10"
    incremental_lookback_days = form.get("incremental_lookback_days", "").strip() or "1"

    if profile_url:
        cmd.extend(["--profile-url", profile_url])
    if profile_list:
        cmd.extend(["--profile-list", profile_list])
    if target_video_id:
        cmd.extend(["--target-video-id", target_video_id])

    cmd.extend(["--cdp-url", cdp_url])
    cmd.extend(["--retries", retries])
    cmd.extend(["--min-delay", min_delay, "--max-delay", max_delay])
    cmd.extend(["--limit", limit])
    cmd.extend(["--max-tabs", max_tabs])
    cmd.extend(["--incremental-daily-max", incremental_daily_max])
    cmd.extend(["--incremental-lookback-days", incremental_lookback_days])
    cmd.extend(["--out", out_path, "--evidence-dir", evidence_dir])

    if form.get("all_mode") == "on":
        cmd.append("--all")
    if form.get("humanize") == "on":
        cmd.append("--humanize")
    if form.get("incremental") == "on":
        cmd.append("--incremental")
    if form.get("close_extra_tabs") == "on":
        cmd.append("--close-extra-tabs")
    if form.get("no_keep_awake") == "on":
        cmd.append("--no-keep-awake")
    if form.get("disable_smart_incremental_window") == "on":
        cmd.append("--disable-smart-incremental-window")

    return cmd, out_path, evidence_dir


def stream_logs(proc: subprocess.Popen[str]) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        with JOB.lock:
            JOB.logs.append(line.rstrip("\n"))
            if len(JOB.logs) > 2000:
                JOB.logs = JOB.logs[-2000:]
    proc.wait()
    with JOB.lock:
        JOB.returncode = proc.returncode
        JOB.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        JOB.process = None


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/run")
def run_job():
    with JOB.lock:
        if JOB.process is not None:
            return jsonify({"ok": False, "error": "A job is already running"}), 409
        cmd, out_path, evidence_dir = build_command(request.form.to_dict())
        JOB.reset()
        JOB.command = cmd
        JOB.out_file = out_path
        JOB.evidence_dir = evidence_dir
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        JOB.process = proc
        thread = threading.Thread(target=stream_logs, args=(proc,), daemon=True)
        thread.start()
    return jsonify({"ok": True})


@app.post("/api/stop")
def stop_job():
    with JOB.lock:
        proc = JOB.process
    if proc is None:
        return jsonify({"ok": False, "error": "No running job"}), 409
    proc.terminate()
    return jsonify({"ok": True})


@app.get("/api/status")
def status():
    with JOB.lock:
        running = JOB.process is not None
        payload = {
            "running": running,
            "started_at": JOB.started_at,
            "finished_at": JOB.finished_at,
            "returncode": JOB.returncode,
            "command": JOB.command,
            "out_file": JOB.out_file,
            "evidence_dir": JOB.evidence_dir,
            "logs": JOB.logs[-300:],
        }
    return jsonify(payload)


@app.get("/api/outputs")
def outputs():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(OUTPUTS_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
        files.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return jsonify({"files": files})


@app.get("/download/<path:filename>")
def download_output(filename: str):
    return send_from_directory(OUTPUTS_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5088, debug=False)
