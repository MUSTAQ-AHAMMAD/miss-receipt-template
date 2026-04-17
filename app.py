"""
================================================================================
ORACLE FUSION FINANCIAL INTEGRATION — WEB UI
================================================================================
Flask-based web interface for the Oracle Fusion Integration pipeline.
Upload input files, configure settings, generate and download outputs.
================================================================================
"""

from __future__ import annotations

import io
import json
import os
import queue
import sys
import threading
import traceback
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
    stream_with_context,
)
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
# Use a fixed secret key from the environment for session stability across restarts;
# falls back to a random key for development only.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # 512 MB

# Upload directory is configurable via the UPLOAD_DIR environment variable.
UPLOAD_BASE = Path(os.environ.get("UPLOAD_DIR", "/tmp/oracle_fusion_ui"))
UPLOAD_BASE.mkdir(parents=True, exist_ok=True)

# In-memory session store: session_id → {queue, status, output_dir, zip_path}
SESSIONS: Dict[str, dict] = {}
SESSIONS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_session() -> str:
    sid = str(uuid.uuid4())
    work_dir = UPLOAD_BASE / sid
    work_dir.mkdir(parents=True, exist_ok=True)
    with SESSIONS_LOCK:
        SESSIONS[sid] = {
            "q":          queue.Queue(),
            "status":     "idle",   # idle | running | done | error
            "output_dir": str(work_dir / "ORACLE_FUSION_OUTPUT"),
            "zip_path":   None,
            "work_dir":   str(work_dir),
        }
    return sid


def _session(sid: str) -> Optional[dict]:
    with SESSIONS_LOCK:
        return SESSIONS.get(sid)


def _save_upload(sid: str, field: str) -> Optional[str]:
    """Save an uploaded file and return its path, or None if not uploaded."""
    f = request.files.get(field)
    if not f or not f.filename:
        return None
    safe_name = secure_filename(f.filename)
    if not safe_name:
        return None
    sess = _session(sid)
    dest = Path(sess["work_dir"]) / safe_name
    f.save(str(dest))
    return str(dest)


# ---------------------------------------------------------------------------
# Background processing thread
# ---------------------------------------------------------------------------

def _run_integration(sid: str, cfg: dict):
    sess = _session(sid)
    q    = sess["q"]

    def log(msg: str):
        q.put({"type": "log", "msg": msg})

    def progress(pct: int, label: str):
        q.put({"type": "progress", "pct": pct, "label": label})

    def stat(key: str, value: str):
        q.put({"type": "stat", "key": key, "value": value})

    try:
        with SESSIONS_LOCK:
            SESSIONS[sid]["status"] = "running"

        # ── redirect stdout so print() calls appear in the log ──
        class _QueueWriter(io.TextIOBase):
            def write(self, s):
                if s.strip():
                    log(s.rstrip())
                return len(s)
            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = _QueueWriter()

        try:
            # Lazy import of the integration module
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "oracle_integration",
                Path(__file__).parent / "Odoo-export-FBDA-template.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            progress(10, "AR Invoice loaded — initialising engine…")

            # Override AR_STATIC comments with org name from config
            if cfg.get("org_name"):
                mod.AR_STATIC["Comments"] = cfg["org_name"]

            integration = mod.OracleFusionIntegration(
                output_dir         = sess["output_dir"],
                start_seq          = int(cfg.get("start_seq", 1)),
                start_legacy_seq_1 = int(cfg.get("start_leg1", 1)),
                start_legacy_seq_2 = int(cfg.get("start_leg2", 1)),
            )

            progress(20, "Loading reference data files…")

            integration.load_from_ar_invoice(
                ar_invoice_path      = cfg["ar_invoice"],
                metadata_path        = cfg["metadata"],
                receipt_methods_path = cfg.get("receipt_methods", ""),
                bank_charges_path    = cfg.get("bank_charges", ""),
            )

            progress(50, "Generating Standard Receipts…")
            std_rcp = integration.generate_standard_receipts()
            integration.save_standard_receipts(std_rcp)
            stat("Standard Receipts", f"{len(std_rcp):,} files")

            progress(75, "Generating Miscellaneous Receipts…")
            misc_rcp = integration.generate_misc_receipts()
            integration.save_misc_receipts(misc_rcp)
            stat("Misc Receipts", f"{len(misc_rcp):,} files")

            progress(90, "Writing verification report…")
            integration._write_ar_invoice_crosscheck(std_rcp)
            integration.vlog.close()
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = Path(sess["output_dir"]) / f"Verification_Report_{ts}.txt"
            integration.vlog.write(log_path)

            progress(95, "Creating download ZIP…")
            zip_path = str(Path(sess["work_dir"]) / "oracle_fusion_output.zip")
            _zip_output(sess["output_dir"], zip_path)

            with SESSIONS_LOCK:
                SESSIONS[sid]["zip_path"] = zip_path
                SESSIONS[sid]["status"]   = "done"

            progress(100, "Complete ✅")
            q.put({"type": "done"})

        finally:
            sys.stdout = old_stdout

    except Exception as exc:
        tb = traceback.format_exc()
        log(f"❌ ERROR: {exc}")
        for line in tb.splitlines():
            log(line)
        with SESSIONS_LOCK:
            SESSIONS[sid]["status"] = "error"
        q.put({"type": "error", "msg": str(exc)})


def _zip_output(output_dir: str, zip_path: str):
    out = Path(output_dir)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if out.exists():
            for fpath in out.rglob("*"):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(out.parent))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/test-report")
def test_report():
    p = Path(__file__).parent / "TEST_REPORT.html"
    if p.exists():
        return p.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}
    return "Test report not found", 404


@app.route("/api/session", methods=["POST"])
def create_session():
    sid = _new_session()
    return jsonify({"session_id": sid})


@app.route("/api/run", methods=["POST"])
def run_integration():
    sid = request.form.get("session_id")
    if not sid or not _session(sid):
        sid = _new_session()

    sess = _session(sid)
    if sess["status"] == "running":
        return jsonify({"error": "Already running"}), 409

    cfg = {}

    # AR Invoice is the only user-uploaded file
    ar_invoice_path = _save_upload(sid, "ar_invoice")
    if ar_invoice_path:
        cfg["ar_invoice"] = ar_invoice_path

    # Auto-load all reference files from the repo root directory
    repo_dir = Path(__file__).parent
    if "ar_invoice" not in cfg:
        # Also try a fallback repo-level AR Invoice (for dev/testing)
        pass

    for key, filename in [
        ("metadata",        "RCPT_Mapping_DATA.csv"),
        ("receipt_methods", "Receipt_Methods.csv"),
        ("bank_charges",    "BANK_CHARGES.csv"),
    ]:
        p = repo_dir / filename
        if p.exists():
            cfg[key] = str(p)

    # Validate the single required file
    if "ar_invoice" not in cfg:
        return jsonify({"error": "Required file 'AR Invoice CSV' is missing."}), 400
    if "metadata" not in cfg:
        return jsonify({"error": "Reference file RCPT_Mapping_DATA.csv not found in server root."}), 400

    # Configuration values
    cfg["org_name"]   = request.form.get("org_name", "AlQurashi-KSA")
    cfg["start_seq"]  = request.form.get("start_seq", "1")
    cfg["start_leg1"] = request.form.get("start_leg1", "1")
    cfg["start_leg2"] = request.form.get("start_leg2", "1")

    # Reset queue / status
    with SESSIONS_LOCK:
        SESSIONS[sid]["q"]        = queue.Queue()
        SESSIONS[sid]["status"]   = "idle"
        SESSIONS[sid]["zip_path"] = None

    thread = threading.Thread(target=_run_integration, args=(sid, cfg), daemon=True)
    thread.start()

    return jsonify({"session_id": sid, "status": "started"})


@app.route("/api/stream/<sid>")
def stream(sid: str):
    sess = _session(sid)
    if not sess:
        return Response("data: {\"type\":\"error\",\"msg\":\"Session not found\"}\n\n",
                        mimetype="text/event-stream")

    @stream_with_context
    def generate():
        q = sess["q"]
        while True:
            try:
                item = q.get(timeout=30)
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                # keep-alive ping
                yield "data: {\"type\":\"ping\"}\n\n"
                if sess["status"] in ("done", "error"):
                    break

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/status/<sid>")
def status(sid: str):
    sess = _session(sid)
    if not sess:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "status":   sess["status"],
        "has_zip":  sess["zip_path"] is not None,
    })


@app.route("/api/download/<sid>")
def download(sid: str):
    sess = _session(sid)
    if not sess or not sess.get("zip_path"):
        return jsonify({"error": "No output available"}), 404
    zip_path = sess["zip_path"]
    if not Path(zip_path).exists():
        return jsonify({"error": "ZIP not found"}), 404
    return send_file(
        zip_path,
        as_attachment=True,
        download_name="oracle_fusion_output.zip",
        mimetype="application/zip",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
