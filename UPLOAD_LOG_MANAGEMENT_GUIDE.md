# Upload Log Management System - Implementation Guide

## Overview

This document describes the comprehensive upload log management and tracking system implemented for Oracle Fusion receipt uploads. The system provides detailed logging of API requests, responses, upload status, and error tracking.

## Problem Solved

**Previous Issue:**
- Logs showing only "Row 2: HTTP 401" without context
- No tracking of what was sent to the API
- No history of upload attempts
- Difficult to diagnose failures

**Solution:**
- Complete request/response logging
- Persistent upload history database
- Detailed error tracking with row-level precision
- API payload and response capture
- Comprehensive reporting dashboard

## Architecture

### Components

1. **UploadLogger** (`upload_logger.py`)
   - SQLite-based persistent logging
   - Tracks upload attempts, status, and metadata
   - Records API requests and responses
   - Generates detailed reports

2. **UploadManager** (`upload_manager.py`)
   - Handles receipt file uploads to Oracle API
   - Implements retry logic with exponential backoff
   - Integrates with UploadLogger for tracking
   - Supports both individual and batch uploads

3. **Flask API Endpoints** (`app.py`)
   - REST API for querying upload logs
   - Export functionality
   - Test upload capabilities

4. **Upload Logs Dashboard** (`templates/upload_logs.html`)
   - Visual interface for monitoring uploads
   - Filter by status and type
   - View detailed API logs
   - Export reports

## Database Schema

### upload_logs Table
```sql
CREATE TABLE upload_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    receipt_type TEXT NOT NULL,          -- STANDARD or MISC
    status TEXT NOT NULL,                 -- SUCCESS, FAILED, PENDING
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT,
    file_size INTEGER,
    row_count INTEGER,
    amount_total REAL,
    payment_method TEXT,
    store_name TEXT,
    date_range TEXT,
    error_message TEXT,
    error_row INTEGER,                    -- Row number where error occurred
    retry_count INTEGER DEFAULT 0,
    last_retry TIMESTAMP,
    completed_date TIMESTAMP
)
```

### api_logs Table
```sql
CREATE TABLE api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id INTEGER,
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_timestamp TIMESTAMP,
    http_method TEXT,
    api_endpoint TEXT,
    request_headers TEXT,                 -- JSON
    request_payload TEXT,                 -- JSON
    response_status INTEGER,              -- HTTP status code
    response_headers TEXT,                -- JSON
    response_body TEXT,                   -- JSON
    duration_ms INTEGER,
    FOREIGN KEY (upload_id) REFERENCES upload_logs(id)
)
```

## Usage

### 1. Basic Upload Logging

```python
from upload_logger import UploadLogger
from upload_manager import UploadManager

# Initialize
logger = UploadLogger()
manager = UploadManager(
    api_endpoint="https://your-oracle-instance.com/api",
    api_key="your-api-key",
    logger=logger
)

# Upload a single receipt file
success, error, upload_id = manager.upload_receipt_file(
    file_path="/path/to/Receipt_CASH_ALARIDAH_20260305.csv",
    receipt_type="STANDARD",
    session_id="optional-session-id"
)

if success:
    print(f"Upload successful! ID: {upload_id}")
else:
    print(f"Upload failed: {error}")
```

### 2. Batch Upload

```python
# Upload all receipts from a directory
results = manager.upload_batch(
    receipt_dir="/path/to/Receipts",
    receipt_type="STANDARD",  # or None for auto-detect
    session_id="batch-001"
)

print(f"Total: {results['total']}")
print(f"Successful: {results['successful']}")
print(f"Failed: {results['failed']}")

for failure in results['failures']:
    print(f"Failed: {failure['filename']} - {failure['error']}")
```

### 3. Query Upload History

```python
from upload_logger import UploadLogger

logger = UploadLogger()

# Get all failed uploads
failed = logger.get_upload_history(
    status="FAILED",
    limit=50
)

for upload in failed:
    print(f"#{upload['id']}: {upload['filename']}")
    print(f"  Error: {upload['error_message']}")
    print(f"  Row: {upload['error_row']}")
```

### 4. View Detailed Upload Information

```python
# Get detailed info including API logs
details = logger.get_upload_details(upload_id=123)

print(f"File: {details['filename']}")
print(f"Status: {details['status']}")

for api_log in details['api_logs']:
    print(f"  Request: {api_log['http_method']} {api_log['api_endpoint']}")
    print(f"  Status: {api_log['response_status']}")
    print(f"  Duration: {api_log['duration_ms']}ms")
```

### 5. Generate Reports

```python
# Export to text file
logger.export_report(
    output_path="/path/to/upload_report.txt",
    status="FAILED"  # Optional filter
)

# Get summary statistics
stats = logger.get_summary_stats()
print(f"Total Uploads: {stats['overall']['total_uploads']}")
print(f"Success Rate: {stats['overall']['successful'] / stats['overall']['total_uploads'] * 100:.1f}%")
```

## API Endpoints

### GET /api/upload-logs/history
Query upload history with filters.

**Parameters:**
- `limit` (int): Max records to return (default: 100)
- `status` (string): Filter by status (SUCCESS, FAILED, PENDING)
- `type` (string): Filter by type (STANDARD, MISC)

**Response:**
```json
{
  "history": [
    {
      "id": 1,
      "filename": "Receipt_CASH_ALARIDAH_20260305.csv",
      "receipt_type": "STANDARD",
      "status": "FAILED",
      "error_message": "Row 2: HTTP 401",
      "upload_date": "2026-04-19T17:30:00",
      ...
    }
  ],
  "count": 1
}
```

### GET /api/upload-logs/details/{upload_id}
Get detailed information including API logs.

**Response:**
```json
{
  "id": 1,
  "filename": "Receipt_CASH_ALARIDAH_20260305.csv",
  "status": "FAILED",
  "error_message": "Row 2: HTTP 401",
  "api_logs": [
    {
      "request_timestamp": "2026-04-19T17:30:00",
      "http_method": "POST",
      "api_endpoint": "https://oracle.com/api/receipts/standard",
      "request_payload": "{...}",
      "response_status": 401,
      "response_body": "{\"error\": \"Unauthorized\"}",
      "duration_ms": 234
    }
  ]
}
```

### GET /api/upload-logs/stats
Get summary statistics.

**Response:**
```json
{
  "overall": {
    "total_uploads": 150,
    "successful": 120,
    "failed": 25,
    "pending": 5,
    "standard_receipts": 100,
    "misc_receipts": 50,
    "total_retries": 15
  },
  "recent_failures": [
    {
      "filename": "Receipt_CASH_ALARIDAH_20260305.csv",
      "error": "Row 2: HTTP 401",
      "date": "2026-04-19T17:30:00"
    }
  ]
}
```

### POST /api/upload-logs/export
Export logs to text report.

**Form Parameters:**
- `status` (optional): Filter by status

**Response:** Text file download

### POST /api/upload-logs/test-upload
Test upload functionality (mock mode).

**Form Parameters:**
- `file_path`: Path to receipt file
- `receipt_type`: STANDARD or MISC
- `session_id` (optional)

**Response:**
```json
{
  "success": false,
  "error": "HTTP 401: Authentication failed",
  "upload_id": 123
}
```

### POST /api/upload-logs/batch-upload
Upload all receipts from a directory.

**Form Parameters:**
- `receipt_dir`: Directory path
- `receipt_type` (optional): STANDARD, MISC, or auto-detect
- `session_id` (optional)

**Response:**
```json
{
  "total": 10,
  "successful": 8,
  "failed": 2,
  "failures": [
    {
      "filename": "Receipt_CASH_01.csv",
      "error": "HTTP 401: Authentication failed",
      "upload_id": 124
    }
  ]
}
```

## Web Dashboard

Access the upload logs dashboard at: `http://localhost:5000/upload-logs`

### Features:
- **Statistics Overview**: Total uploads, success/failure counts
- **Filter Options**: By status (Success/Failed/Pending) and type (Standard/Misc)
- **Interactive Table**: Click any row to view detailed information
- **Detailed View**:
  - Upload metadata
  - Full API request payload
  - Full API response
  - Error details with row numbers
  - Retry information
- **Export**: Download complete report as text file

## Log Report Format

The exported text report includes:

```
================================================================================
RECEIPT UPLOAD LOG REPORT
================================================================================
Generated: 2026-04-19 17:30:00

SUMMARY STATISTICS
--------------------------------------------------------------------------------
Total Uploads:       150
  Successful:        120
  Failed:            25
  Pending:           5
Standard Receipts:   100
Misc Receipts:       50
Total Retries:       15

RECENT FAILURES
--------------------------------------------------------------------------------
[2026-04-19 17:30:00] Receipt_CASH_ALARIDAH_20260305.csv
  Error: Row 2: HTTP 401

DETAILED UPLOAD LOG
--------------------------------------------------------------------------------
ID     Filename                                      Status     Date
--------------------------------------------------------------------------------
#2     Receipt_CASH_ALARIDAH_20260305.csv            FAILED     2026-04-19 17:30:00
       Error: Row 2: HTTP 401
       Method: Cash, Rows: 45, Total: 15250.00 SAR

#1     Receipt_CASH_ALARIDAH_20260305.csv            FAILED     2026-04-19 17:20:00
       Error: Row 2: HTTP 401
       Method: Cash, Rows: 45, Total: 15250.00 SAR
```

## Error Messages

The system captures detailed error information:

- **HTTP 401**: Authentication failure (API key invalid)
- **HTTP 400**: Validation error (includes row number if available)
- **HTTP 500**: Server error
- **Row-level errors**: Extracted from API response when available

Example error message:
```
Row 2: HTTP 401 - Invalid customer account number
```

## Configuration

### Setting Up Real API Upload

To connect to the actual Oracle Fusion API:

1. Edit `upload_manager.py`:
   ```python
   def __init__(self, api_endpoint: str = None, api_key: str = None, ...):
       self.api_endpoint = api_endpoint or "https://your-actual-oracle-instance.com/fscmRestApi/..."
       self.api_key = api_key or os.environ.get("ORACLE_API_KEY")
       self.mock_mode = False  # Set to False for real API calls
   ```

2. Uncomment and configure the real API call in `_attempt_upload()`:
   ```python
   import requests
   response = requests.post(endpoint, json=payload, headers=headers)
   response_status = response.status_code
   response_body = response.json()
   ```

3. Set environment variable:
   ```bash
   export ORACLE_API_KEY="your-actual-api-key"
   ```

## Retry Logic

The system implements exponential backoff for retries:
- **Max Retries**: 3 attempts (configurable)
- **Backoff**: 2^attempt seconds (2s, 4s, 8s)
- **Retry Tracking**: All retry attempts are logged

## Best Practices

1. **Monitor the Dashboard**: Check `/upload-logs` regularly for failed uploads
2. **Review Failed Uploads**: Use the detailed view to inspect API payloads and responses
3. **Export Regular Reports**: Generate periodic reports for auditing
4. **Act on 401 Errors**: Update API credentials immediately
5. **Investigate Row Errors**: Check the specific row mentioned in error messages

## Troubleshooting

### Database Locked Error
If you see "database is locked" errors, ensure only one process is writing to the database at a time.

### Missing Upload Logs
Logs are stored in `upload_logs.db` in the project root. If deleted, the database will be recreated automatically.

### API Endpoint Not Found (501)
This means the system is in mock mode. Configure real API endpoints to enable actual uploads.

## Future Enhancements

Potential improvements:
- Email notifications for failed uploads
- Scheduled retry of failed uploads
- Webhook support for external monitoring
- Advanced analytics and trends
- Multi-tenant support with separate databases

## Support

For issues or questions:
1. Check the upload logs dashboard at `/upload-logs`
2. Export detailed logs using the export function
3. Review API request/response logs for specific uploads
4. Check the `upload_logs.db` database directly if needed
