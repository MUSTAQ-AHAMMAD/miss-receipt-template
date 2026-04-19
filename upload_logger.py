"""
================================================================================
UPLOAD LOGGER - Receipt Upload Tracking and Log Management
================================================================================
Tracks upload attempts, API payloads, responses, and maintains detailed logs
for both Standard and Miscellaneous receipt uploads.
================================================================================
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading


class UploadLogger:
    """
    Manages upload tracking and detailed logging for receipt files.
    Stores upload attempts, API requests/responses, and maintains history.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the upload logger.

        Args:
            db_path: Path to SQLite database file. Defaults to upload_logs.db
        """
        if db_path is None:
            db_path = str(Path(__file__).parent / "upload_logs.db")

        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main upload tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upload_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    receipt_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    file_size INTEGER,
                    row_count INTEGER,
                    amount_total REAL,
                    payment_method TEXT,
                    store_name TEXT,
                    date_range TEXT,
                    error_message TEXT,
                    error_row INTEGER,
                    retry_count INTEGER DEFAULT 0,
                    last_retry TIMESTAMP,
                    completed_date TIMESTAMP
                )
            """)

            # API request/response logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    upload_id INTEGER,
                    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_timestamp TIMESTAMP,
                    http_method TEXT,
                    api_endpoint TEXT,
                    request_headers TEXT,
                    request_payload TEXT,
                    response_status INTEGER,
                    response_headers TEXT,
                    response_body TEXT,
                    duration_ms INTEGER,
                    FOREIGN KEY (upload_id) REFERENCES upload_logs(id)
                )
            """)

            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_status
                ON upload_logs(status, upload_date)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_filename
                ON upload_logs(filename)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_upload_session
                ON upload_logs(session_id)
            """)

            conn.commit()

    def log_upload_start(
        self,
        filename: str,
        receipt_type: str,
        session_id: str = None,
        file_size: int = None,
        row_count: int = None,
        amount_total: float = None,
        payment_method: str = None,
        store_name: str = None,
        date_range: str = None
    ) -> int:
        """
        Log the start of an upload attempt.

        Returns:
            upload_id: Unique ID for this upload attempt
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO upload_logs (
                        filename, receipt_type, status, session_id,
                        file_size, row_count, amount_total,
                        payment_method, store_name, date_range
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    filename, receipt_type, "PENDING", session_id,
                    file_size, row_count, amount_total,
                    payment_method, store_name, date_range
                ))
                conn.commit()
                return cursor.lastrowid

    def log_api_request(
        self,
        upload_id: int,
        http_method: str,
        api_endpoint: str,
        request_headers: Dict[str, str] = None,
        request_payload: Any = None
    ) -> int:
        """
        Log an API request being sent.

        Returns:
            api_log_id: Unique ID for this API call
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Convert headers and payload to JSON
                headers_json = json.dumps(request_headers) if request_headers else None

                # Handle different payload types
                if request_payload is not None:
                    if isinstance(request_payload, (dict, list)):
                        payload_json = json.dumps(request_payload, indent=2)
                    else:
                        payload_json = str(request_payload)
                else:
                    payload_json = None

                cursor.execute("""
                    INSERT INTO api_logs (
                        upload_id, http_method, api_endpoint,
                        request_headers, request_payload
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    upload_id, http_method, api_endpoint,
                    headers_json, payload_json
                ))
                conn.commit()
                return cursor.lastrowid

    def log_api_response(
        self,
        api_log_id: int,
        response_status: int,
        response_headers: Dict[str, str] = None,
        response_body: Any = None,
        duration_ms: int = None
    ):
        """Log the API response received"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                headers_json = json.dumps(response_headers) if response_headers else None

                if response_body is not None:
                    if isinstance(response_body, (dict, list)):
                        body_json = json.dumps(response_body, indent=2)
                    else:
                        body_json = str(response_body)
                else:
                    body_json = None

                cursor.execute("""
                    UPDATE api_logs SET
                        response_timestamp = CURRENT_TIMESTAMP,
                        response_status = ?,
                        response_headers = ?,
                        response_body = ?,
                        duration_ms = ?
                    WHERE id = ?
                """, (
                    response_status, headers_json, body_json,
                    duration_ms, api_log_id
                ))
                conn.commit()

    def update_upload_status(
        self,
        upload_id: int,
        status: str,
        error_message: str = None,
        error_row: int = None,
        is_retry: bool = False
    ):
        """
        Update the status of an upload attempt.

        Args:
            upload_id: Upload ID from log_upload_start
            status: SUCCESS, FAILED, or PENDING
            error_message: Error details if failed
            error_row: Row number where error occurred
            is_retry: Whether this is a retry attempt
        """
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if is_retry:
                    cursor.execute("""
                        UPDATE upload_logs SET
                            status = ?,
                            error_message = ?,
                            error_row = ?,
                            retry_count = retry_count + 1,
                            last_retry = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, error_message, error_row, upload_id))
                else:
                    completed = datetime.now().isoformat() if status == "SUCCESS" else None
                    cursor.execute("""
                        UPDATE upload_logs SET
                            status = ?,
                            error_message = ?,
                            error_row = ?,
                            completed_date = ?
                        WHERE id = ?
                    """, (status, error_message, error_row, completed, upload_id))

                conn.commit()

    def get_upload_history(
        self,
        limit: int = 100,
        status: str = None,
        receipt_type: str = None
    ) -> List[Dict]:
        """
        Retrieve upload history.

        Args:
            limit: Maximum number of records to return
            status: Filter by status (SUCCESS, FAILED, PENDING)
            receipt_type: Filter by type (STANDARD, MISC)

        Returns:
            List of upload records with details
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM upload_logs WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)

            if receipt_type:
                query += " AND receipt_type = ?"
                params.append(receipt_type)

            query += " ORDER BY upload_date DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_upload_details(self, upload_id: int) -> Optional[Dict]:
        """Get detailed information about a specific upload including API logs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get upload record
            cursor.execute("SELECT * FROM upload_logs WHERE id = ?", (upload_id,))
            upload = cursor.fetchone()

            if not upload:
                return None

            upload_dict = dict(upload)

            # Get associated API logs
            cursor.execute("""
                SELECT * FROM api_logs
                WHERE upload_id = ?
                ORDER BY request_timestamp
            """, (upload_id,))

            api_logs = [dict(row) for row in cursor.fetchall()]
            upload_dict['api_logs'] = api_logs

            return upload_dict

    def get_summary_stats(self) -> Dict:
        """Get summary statistics of all uploads"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_uploads,
                    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN receipt_type = 'STANDARD' THEN 1 ELSE 0 END) as standard_receipts,
                    SUM(CASE WHEN receipt_type = 'MISC' THEN 1 ELSE 0 END) as misc_receipts,
                    SUM(retry_count) as total_retries
                FROM upload_logs
            """)

            overall = dict(cursor.fetchone())

            # Recent failures
            cursor.execute("""
                SELECT filename, error_message, upload_date
                FROM upload_logs
                WHERE status = 'FAILED'
                ORDER BY upload_date DESC
                LIMIT 10
            """)

            recent_failures = [
                {
                    'filename': row[0],
                    'error': row[1],
                    'date': row[2]
                }
                for row in cursor.fetchall()
            ]

            return {
                'overall': overall,
                'recent_failures': recent_failures
            }

    def export_report(self, output_path: str, status: str = None):
        """
        Export upload logs to a detailed text report.

        Args:
            output_path: Path for the output report file
            status: Filter by status (None = all)
        """
        records = self.get_upload_history(limit=1000, status=status)
        stats = self.get_summary_stats()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("RECEIPT UPLOAD LOG REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")

            # Summary stats
            f.write("SUMMARY STATISTICS\n")
            f.write("-"*80 + "\n")
            overall = stats['overall']
            f.write(f"Total Uploads:       {overall['total_uploads']}\n")
            f.write(f"  Successful:        {overall['successful']}\n")
            f.write(f"  Failed:            {overall['failed']}\n")
            f.write(f"  Pending:           {overall['pending']}\n")
            f.write(f"Standard Receipts:   {overall['standard_receipts']}\n")
            f.write(f"Misc Receipts:       {overall['misc_receipts']}\n")
            f.write(f"Total Retries:       {overall['total_retries']}\n")
            f.write("\n")

            # Recent failures
            if stats['recent_failures']:
                f.write("RECENT FAILURES\n")
                f.write("-"*80 + "\n")
                for failure in stats['recent_failures']:
                    f.write(f"[{failure['date']}] {failure['filename']}\n")
                    f.write(f"  Error: {failure['error']}\n")
                    f.write("\n")

            # Detailed records
            f.write("DETAILED UPLOAD LOG\n")
            f.write("-"*80 + "\n")
            f.write(f"{'ID':<6} {'Filename':<45} {'Status':<10} {'Date':<20}\n")
            f.write("-"*80 + "\n")

            for record in records:
                f.write(f"#{record['id']:<5} {record['filename']:<45} {record['status']:<10} {record['upload_date']:<20}\n")
                if record['error_message']:
                    f.write(f"       Error: {record['error_message']}\n")
                if record['payment_method']:
                    f.write(f"       Method: {record['payment_method']}, Rows: {record['row_count']}, Total: {record['amount_total']:.2f} SAR\n")
                f.write("\n")
