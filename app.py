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

# Tolerance used when comparing AR Invoice total to input sheet total
_TOTAL_MATCH_THRESHOLD = 0.01


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

            progress(10, "Initialising integration engine…")

            # Override AR_STATIC comments with org name from config
            if cfg.get("org_name"):
                mod.AR_STATIC["Comments"] = cfg["org_name"]

            # Enable sequence manager if auto-increment is requested
            use_seq_mgr = cfg.get("auto_increment", "false").lower() == "true"

            integration = mod.OracleFusionIntegration(
                output_dir           = sess["output_dir"],
                start_seq            = int(cfg.get("start_seq", 1)),
                start_legacy_seq_1   = int(cfg.get("start_leg1", 1)),
                start_legacy_seq_2   = int(cfg.get("start_leg2", 1)),
                use_sequence_manager = use_seq_mgr,
            )

            mode = cfg.get("mode", "ar_invoice")

            if mode == "sales_payment":
                # ── GENERATE FROM SCRATCH (Sales Lines + Payment Lines) ──
                progress(15, "Loading reference data files…")

                integration.load_data(
                    line_items_path      = cfg["sales_lines"],
                    payments_path        = cfg["payment_lines"],
                    metadata_path        = cfg["metadata"],
                    registers_path       = cfg.get("registers", ""),
                    receipt_methods_path = cfg.get("receipt_methods", ""),
                    bank_charges_path    = cfg.get("bank_charges", ""),
                )

                progress(35, "Generating AR Invoice…")
                ar_df = integration.generate_ar_invoices()
                integration.save_ar(ar_df)

                ar_total     = float(ar_df["Transaction Line Amount"].sum())
                ar_row_count = len(ar_df)
                stat("AR Invoice Lines", f"{ar_row_count:,}")
                stat("AR Invoice Total", f"{ar_total:,.2f} SAR")

                # Compute input sheet total from loaded line items
                # Apply same sign alignment logic as AR generation for consistency
                def calculate_adjusted_amount(row):
                    """
                    Apply sign alignment for discount items from Odoo.
                    Odoo exports discount items with negative qty and positive amt.
                    We flip the amount to negative to reduce the invoice total.
                    """
                    qty = mod.safe_float(row.get("Quantity", 0))
                    amt = mod.safe_float(row.get("Subtotal w/o Tax", 0))
                    # Sign alignment for discount items: negative qty + positive amt → negative amt
                    if qty < 0 and amt > 0:
                        return -amt
                    return amt
                
                input_total = float(
                    integration.line_items.apply(calculate_adjusted_amount, axis=1).sum()
                )
                stat("Input Sheet Total", f"{input_total:,.2f} SAR")

                diff = abs(ar_total - input_total)
                match_flag = "✓ MATCH" if diff < _TOTAL_MATCH_THRESHOLD else f"⚠ DIFF {diff:,.2f}"
                stat("Total Match", match_flag)
                
                # Date-wise breakdown comparison
                log("Computing date-wise totals comparison...")
                
                # Group AR by date
                ar_by_date = ar_df.groupby('Transaction Date')['Transaction Line Amount'].sum().to_dict()
                
                # Group input by date
                line_items_with_date = integration.line_items.copy()
                line_items_with_date['adjusted_amount'] = line_items_with_date.apply(calculate_adjusted_amount, axis=1)
                
                # Get date column from line items
                date_col = None
                for col in line_items_with_date.columns:
                    if any(x in col.lower() for x in ['date', 'sale date']):
                        date_col = col
                        break
                
                if date_col:
                    # Format dates consistently
                    line_items_with_date['formatted_date'] = pd.to_datetime(
                        line_items_with_date[date_col], errors='coerce'
                    ).dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    input_by_date = line_items_with_date.groupby('formatted_date')['adjusted_amount'].sum().to_dict()
                    
                    # Build comparison stats
                    date_comparison_text = "\n\nDATE-WISE COMPARISON:\n" + "="*80 + "\n"
                    date_comparison_text += f"{'Date':<22} {'AR Total':>18} {'Input Total':>18} {'Difference':>18}\n"
                    date_comparison_text += "-"*80 + "\n"
                    
                    all_dates = sorted(set(list(ar_by_date.keys()) + list(input_by_date.keys())))
                    for date in all_dates:
                        ar_amt = ar_by_date.get(date, 0)
                        input_amt = input_by_date.get(date, 0)
                        diff_amt = abs(ar_amt - input_amt)
                        match_icon = "✓" if diff_amt < _TOTAL_MATCH_THRESHOLD else "⚠"
                        date_comparison_text += f"{date:<22} {ar_amt:>18,.2f} {input_amt:>18,.2f} {diff_amt:>18,.2f} {match_icon}\n"
                    
                    stat("Date-wise Match", "See verification report for details")
                    
                    # Store for report
                    integration._date_comparison = date_comparison_text
                else:
                    integration._date_comparison = None

                progress(55, "Generating Standard Receipts…")
                std_rcp = integration.generate_standard_receipts()
                integration.save_standard_receipts(std_rcp)
                stat("Standard Receipts", f"{len(std_rcp):,} files")

                progress(75, "Generating Miscellaneous Receipts…")
                misc_rcp = integration.generate_misc_receipts()
                integration.save_misc_receipts(misc_rcp)
                stat("Misc Receipts", f"{len(misc_rcp):,} files")

                progress(90, "Writing verification report…")
                integration._write_final_crosscheck(ar_df, std_rcp)
                integration.vlog.close()
                ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = Path(sess["output_dir"]) / f"Verification_Report_{ts}.txt"
                integration.vlog.write(log_path)
                
                # Copy report to persistent reports directory
                import shutil
                reports_copy = REPORTS_DIR / f"Verification_Report_{ts}.txt"
                shutil.copy2(str(log_path), str(reports_copy))

            else:
                # ── AR INVOICE MODE (default) ──
                progress(20, "Loading reference data files…")

                integration.load_from_ar_invoice(
                    ar_invoice_path      = cfg["ar_invoice"],
                    metadata_path        = cfg["metadata"],
                    receipt_methods_path = cfg.get("receipt_methods", ""),
                    bank_charges_path    = cfg.get("bank_charges", ""),
                    payment_file_path    = cfg.get("payment_file", ""),
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
                
                # Copy report to persistent reports directory
                import shutil
                reports_copy = REPORTS_DIR / f"Verification_Report_{ts}.txt"
                shutil.copy2(str(log_path), str(reports_copy))

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

    cfg  = {}
    mode = request.form.get("mode", "ar_invoice")
    cfg["mode"] = mode

    # Auto-load all reference files from the repo root directory
    repo_dir = Path(__file__).parent

    for key, filename in [
        ("metadata",        "RCPT_Mapping_DATA.csv"),
        ("receipt_methods", "Receipt_Methods.csv"),
        ("bank_charges",    "BANK_CHARGES.csv"),
    ]:
        p = repo_dir / filename
        if p.exists():
            cfg[key] = str(p)

    if mode == "sales_payment":
        # New mode: Sales Lines + Payment Lines → generate AR Invoice
        sales_lines_path   = _save_upload(sid, "sales_lines")
        payment_lines_path = _save_upload(sid, "payment_lines")

        if sales_lines_path:
            cfg["sales_lines"] = sales_lines_path
        if payment_lines_path:
            cfg["payment_lines"] = payment_lines_path

        if "sales_lines" not in cfg:
            return jsonify({"error": "Required file 'Sales Lines CSV/XLSX' is missing."}), 400
        if "payment_lines" not in cfg:
            return jsonify({"error": "Required file 'Payment Lines CSV/XLSX' is missing."}), 400
        if "metadata" not in cfg:
            return jsonify({"error": "Reference file RCPT_Mapping_DATA.csv not found in server root."}), 400

    else:
        # Existing AR Invoice mode
        ar_invoice_path = _save_upload(sid, "ar_invoice")
        if ar_invoice_path:
            cfg["ar_invoice"] = ar_invoice_path

        # Optional payment file
        payment_file_path = _save_upload(sid, "payment_file")
        if payment_file_path:
            cfg["payment_file"] = payment_file_path

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


@app.route("/api/merge-csv", methods=["POST"])
def merge_csv_files():
    """Merge multiple AR Invoice CSV files"""
    try:
        import csv_merger
        
        # Create a temporary session for the merge
        sid = _new_session()
        sess = _session(sid)
        work_dir = Path(sess["work_dir"])
        
        # Save all uploaded files
        files = request.files.getlist("csv_files")
        if not files or len(files) < 2:
            return jsonify({"error": "Please upload at least 2 CSV files"}), 400
        
        input_paths = []
        for f in files:
            if f and f.filename:
                safe_name = secure_filename(f.filename)
                dest = work_dir / safe_name
                f.save(str(dest))
                input_paths.append(str(dest))
        
        # Merge the files
        output_path = work_dir / "merged_ar_invoice.csv"
        stats = csv_merger.merge_ar_invoices(input_paths, str(output_path))
        
        # Return the merged file
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name="merged_ar_invoice.csv",
            mimetype="text/csv",
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-report", methods=["POST"])
def generate_comprehensive_report():
    """Generate comprehensive report for uploaded files"""
    try:
        import report_generator
        
        sid = _new_session()
        sess = _session(sid)
        work_dir = Path(sess["work_dir"])
        report_dir = work_dir / "REPORTS"
        
        report_type = request.form.get("report_type", "ar")
        generator = report_generator.ComprehensiveReportGenerator(str(report_dir))
        
        if report_type == "ar":
            # AR Invoice report
            ar_file = _save_upload(sid, "ar_invoice")
            if not ar_file:
                return jsonify({"error": "AR Invoice file required"}), 400
            
            metadata_file = _save_upload(sid, "metadata")
            generator.generate_ar_invoice_report(ar_file, metadata_file)
            
        elif report_type == "subinv":
            # Sub-inventory report
            ar_file = _save_upload(sid, "ar_invoice")
            metadata_file = _save_upload(sid, "metadata")
            
            if not ar_file or not metadata_file:
                return jsonify({"error": "Both AR Invoice and Metadata files required"}), 400
            
            generator.generate_sub_inventory_report(ar_file, metadata_file)
        
        # Zip the reports
        zip_path = work_dir / "reports.zip"
        import zipfile
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in report_dir.rglob("*"):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(report_dir))
        
        return send_file(
            str(zip_path),
            as_attachment=True,
            download_name="comprehensive_reports.zip",
            mimetype="application/zip",
        )
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Directory to store persistent reports
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "/tmp/oracle_fusion_reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/api/reports/list", methods=["GET"])
def list_reports():
    """List all generated reports with metadata"""
    try:
        reports = []
        
        # Scan for verification reports in the reports directory
        for report_file in REPORTS_DIR.glob("*.txt"):
            stat = report_file.stat()
            reports.append({
                "filename": report_file.name,
                "path": str(report_file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "type": "verification"
            })
        
        # Also scan for any previous session outputs
        for session_dir in UPLOAD_BASE.glob("*"):
            if session_dir.is_dir():
                output_dir = session_dir / "ORACLE_FUSION_OUTPUT"
                if output_dir.exists():
                    for report_file in output_dir.glob("Verification_Report_*.txt"):
                        stat = report_file.stat()
                        reports.append({
                            "filename": report_file.name,
                            "path": str(report_file),
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                            "type": "verification",
                            "session": session_dir.name
                        })
        
        # Sort by creation time, newest first
        reports.sort(key=lambda x: x["created"], reverse=True)
        
        return jsonify({"reports": reports})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports/view/<path:filename>", methods=["GET"])
def view_report(filename: str):
    """View a report as text"""
    try:
        # Security: validate filename - only allow alphanumeric, dash, underscore, and .txt extension
        import os
        import re
        
        filename = os.path.basename(filename)  # Prevent directory traversal
        if not re.match(r'^[a-zA-Z0-9_-]+\.txt$', filename):
            return jsonify({"error": "Invalid filename"}), 400
        
        # Try to find the file in reports dir or session dirs
        report_path = None
        
        # Check reports directory
        candidate = REPORTS_DIR / filename
        if candidate.exists() and candidate.is_file():
            report_path = candidate
        else:
            # Check session directories
            for session_dir in UPLOAD_BASE.glob("*"):
                candidate = session_dir / "ORACLE_FUSION_OUTPUT" / filename
                if candidate.exists() and candidate.is_file():
                    report_path = candidate
                    break
        
        if not report_path or not report_path.exists():
            return jsonify({"error": "Report not found"}), 404
        
        content = report_path.read_text(encoding="utf-8")
        return jsonify({
            "filename": filename,
            "content": content,
            "size": len(content)
        })
    
    except Exception as e:
        # Don't expose stack trace to user
        import logging
        logging.error(f"Error viewing report: {e}", exc_info=True)
        return jsonify({"error": "Failed to load report"}), 500


@app.route("/api/reports/download/<path:filename>", methods=["GET"])
def download_report(filename: str):
    """Download a report file"""
    try:
        # Security: validate filename
        import os
        import re
        
        filename = os.path.basename(filename)  # Prevent directory traversal
        if not re.match(r'^[a-zA-Z0-9_-]+\.txt$', filename):
            return jsonify({"error": "Invalid filename"}), 400
        
        # Try to find the file
        report_path = None
        
        # Check reports directory
        candidate = REPORTS_DIR / filename
        if candidate.exists() and candidate.is_file():
            report_path = candidate
        else:
            # Check session directories
            for session_dir in UPLOAD_BASE.glob("*"):
                candidate = session_dir / "ORACLE_FUSION_OUTPUT" / filename
                if candidate.exists() and candidate.is_file():
                    report_path = candidate
                    break
        
        if not report_path or not report_path.exists():
            return jsonify({"error": "Report not found"}), 404
        
        return send_file(
            str(report_path),
            as_attachment=True,
            download_name=filename,
            mimetype="text/plain"
        )
    
    except Exception as e:
        import logging
        logging.error(f"Error downloading report: {e}", exc_info=True)
        return jsonify({"error": "Failed to download report"}), 500


@app.route("/api/reports/download-pdf/<path:filename>", methods=["GET"])
def download_report_pdf(filename: str):
    """Download a report as HTML for browser PDF conversion"""
    try:
        import pdf_report_generator
        import os
        import re
        
        # Security: validate filename
        filename = os.path.basename(filename)  # Prevent directory traversal
        if not re.match(r'^[a-zA-Z0-9_-]+\.txt$', filename):
            return jsonify({"error": "Invalid filename"}), 400
        
        # Try to find the file
        report_path = None
        
        # Check reports directory
        candidate = REPORTS_DIR / filename
        if candidate.exists() and candidate.is_file():
            report_path = candidate
        else:
            # Check session directories
            for session_dir in UPLOAD_BASE.glob("*"):
                candidate = session_dir / "ORACLE_FUSION_OUTPUT" / filename
                if candidate.exists() and candidate.is_file():
                    report_path = candidate
                    break
        
        if not report_path or not report_path.exists():
            return jsonify({"error": "Report not found"}), 404
        
        # Read the text content
        text_content = report_path.read_text(encoding="utf-8")
        
        # Generate HTML for browser-based PDF conversion
        html_content = pdf_report_generator.generate_pdf_from_text(
            text_content,
            title=f"Verification Report - {filename}"
        )
        
        # Return HTML for browser to convert to PDF via print dialog
        pdf_filename = filename.replace('.txt', '.html')
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'inline; filename="{pdf_filename}"'
            }
        )
    
    except Exception as e:
        import logging
        logging.error(f"Error generating report HTML: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate report"}), 500


@app.route("/api/reports/summary-pdf", methods=["POST"])
def generate_summary_pdf():
    """Generate an HTML summary from AR Invoice data for browser-based PDF conversion"""
    try:
        import pdf_report_generator
        
        sid = _new_session()
        sess = _session(sid)
        
        # Get the uploaded AR Invoice file
        ar_file = _save_upload(sid, "ar_invoice")
        if not ar_file:
            return jsonify({"error": "AR Invoice file required"}), 400
        
        # Generate HTML (not actual PDF, for browser conversion)
        html_content = pdf_report_generator.generate_invoice_summary_pdf(ar_file)
        
        # Return HTML for browser to convert to PDF
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': 'inline; filename="ar_invoice_summary.html"'
            }
        )
    
    except Exception as e:
        import logging
        logging.error(f"Error generating summary: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate summary"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
