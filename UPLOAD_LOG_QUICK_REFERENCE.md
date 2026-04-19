# Upload Log Management - Quick Reference

## Problem Statement (Before)

```
ID	Filename	Status	Response	Date
#2	Receipt_CASH_ALARIDAH_20260305.csv	FAILED	Row 2: HTTP 401	4/19/2026
#1	Receipt_CASH_ALARIDAH_20260305.csv	FAILED	Row 2: HTTP 401	4/19/2026
```

**Issues:**
- ❌ No visibility into what was sent to the API
- ❌ No record of the API response details
- ❌ Cannot see the request payload
- ❌ No tracking of retry attempts
- ❌ Limited error information
- ❌ No historical tracking

## Solution (After)

### 1. Complete Upload History

Access: `http://localhost:5000/upload-logs`

**Dashboard View:**
```
┌─────────────────────────────────────────────────────────────┐
│                Upload Logs Dashboard                        │
├─────────────────────────────────────────────────────────────┤
│ Total: 150  │ Success: 120  │ Failed: 25  │ Pending: 5   │
├─────────────────────────────────────────────────────────────┤
│ ID  │ Filename                         │ Status  │ Error   │
├─────────────────────────────────────────────────────────────┤
│ #2  │ Receipt_CASH_ALARIDAH_20260305   │ FAILED  │ Row 2:  │
│     │                                  │         │ HTTP401 │
├─────────────────────────────────────────────────────────────┤
│ #1  │ Receipt_CASH_ALARIDAH_20260305   │ FAILED  │ Row 2:  │
│     │                                  │         │ HTTP401 │
└─────────────────────────────────────────────────────────────┘
```

### 2. Detailed API Logs

Click any upload to see:

**Upload Information:**
```
Upload ID:          #2
Filename:           Receipt_CASH_ALARIDAH_20260305.csv
Receipt Type:       STANDARD
Status:             FAILED
Upload Date:        2026-04-19 17:30:00
Row Count:          45
Total Amount:       15,250.00 SAR
Payment Method:     Cash
Error Message:      Row 2: HTTP 401 - Authentication failed
Error Row:          2
Retry Count:        3
```

**API Request Log:**
```
POST https://oracle.com/fscmRestApi/resources/receipts/standard

Request Headers:
{
  "Content-Type": "application/json",
  "Authorization": "Bearer eyJhbGc..."
}

Request Payload:
{
  "receiptType": "STANDARD",
  "receipts": [
    {
      "ReceiptNumber": "RCPT-001",
      "ReceiptMethod": "Cash",
      "ReceiptDate": "2026-03-05",
      "BusinessUnit": "AlQurashi-KSA",
      "CustomerAccountNumber": "CUST-001",
      "CustomerSite": "SITE-001",
      "Amount": 15250.00,
      "Currency": "SAR",
      "RemittanceBankAccountNumber": "1234567890",
      "AccountingDate": "2026-03-05"
    },
    ...
  ],
  "metadata": {
    "totalRecords": 45,
    "totalAmount": 15250.00
  }
}

Response Status: 401
Response Time: 234ms

Response Body:
{
  "error": "Unauthorized",
  "message": "Invalid or expired API credentials",
  "timestamp": "2026-04-19T17:30:00Z"
}
```

### 3. Summary Statistics

```
SUMMARY STATISTICS
────────────────────────────────────────────────
Total Uploads:       150
  Successful:        120  (80.0%)
  Failed:            25   (16.7%)
  Pending:           5    (3.3%)
Standard Receipts:   100
Misc Receipts:       50
Total Retries:       15
Average Retries:     0.6 per failed upload
```

### 4. Exported Report

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
  Error: Row 2: HTTP 401 - Authentication failed

[2026-04-19 17:20:00] Receipt_CASH_ALARIDAH_20260305.csv
  Error: Row 2: HTTP 401 - Authentication failed

DETAILED UPLOAD LOG
--------------------------------------------------------------------------------
ID     Filename                                      Status     Date
--------------------------------------------------------------------------------
#2     Receipt_CASH_ALARIDAH_20260305.csv            FAILED     2026-04-19 17:30:00
       Error: Row 2: HTTP 401 - Authentication failed
       Method: Cash, Rows: 45, Total: 15250.00 SAR
       Retries: 3, Last Retry: 2026-04-19 17:30:15

#1     Receipt_CASH_ALARIDAH_20260305.csv            FAILED     2026-04-19 17:20:00
       Error: Row 2: HTTP 401 - Authentication failed
       Method: Cash, Rows: 45, Total: 15250.00 SAR
       Retries: 3, Last Retry: 2026-04-19 17:20:15
```

## Usage Examples

### Example 1: Test Single Upload

```bash
# Test uploading a receipt file
curl -X POST http://localhost:5000/api/upload-logs/test-upload \
  -F "file_path=/path/to/Receipt_CASH_ALARIDAH_20260305.csv" \
  -F "receipt_type=STANDARD" \
  -F "session_id=test-001"
```

**Response:**
```json
{
  "success": false,
  "error": "HTTP 401: Authentication failed",
  "upload_id": 2
}
```

### Example 2: View Upload Details

```bash
# Get detailed information about upload #2
curl http://localhost:5000/api/upload-logs/details/2
```

**Response:**
```json
{
  "id": 2,
  "filename": "Receipt_CASH_ALARIDAH_20260305.csv",
  "receipt_type": "STANDARD",
  "status": "FAILED",
  "upload_date": "2026-04-19T17:30:00",
  "row_count": 45,
  "amount_total": 15250.00,
  "payment_method": "Cash",
  "error_message": "HTTP 401: Authentication failed",
  "error_row": 2,
  "retry_count": 3,
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

### Example 3: Batch Upload

```bash
# Upload all receipts from a directory
curl -X POST http://localhost:5000/api/upload-logs/batch-upload \
  -F "receipt_dir=/tmp/oracle_fusion_ui/session-123/ORACLE_FUSION_OUTPUT/Receipts" \
  -F "session_id=batch-001"
```

**Response:**
```json
{
  "total": 10,
  "successful": 8,
  "failed": 2,
  "failures": [
    {
      "filename": "Receipt_CASH_ALARIDAH_20260305.csv",
      "error": "HTTP 401: Authentication failed",
      "upload_id": 2
    },
    {
      "filename": "Receipt_MADA_STORE02_20260306.csv",
      "error": "HTTP 400: Row 5: Invalid customer site",
      "upload_id": 3
    }
  ]
}
```

### Example 4: Query Failed Uploads

```bash
# Get all failed uploads
curl http://localhost:5000/api/upload-logs/history?status=FAILED&limit=50
```

**Response:**
```json
{
  "history": [
    {
      "id": 2,
      "filename": "Receipt_CASH_ALARIDAH_20260305.csv",
      "receipt_type": "STANDARD",
      "status": "FAILED",
      "error_message": "HTTP 401: Authentication failed",
      "upload_date": "2026-04-19T17:30:00",
      "row_count": 45,
      "amount_total": 15250.00
    }
  ],
  "count": 1
}
```

### Example 5: Export Logs

```bash
# Export failed uploads to report
curl -X POST http://localhost:5000/api/upload-logs/export \
  -F "status=FAILED" \
  -o upload_logs_failed.txt
```

## Key Improvements

### ✅ Complete Visibility

| Before | After |
|--------|-------|
| "Row 2: HTTP 401" | Full API request payload logged |
| No response details | Complete response body captured |
| No retry tracking | Retry count and timestamps tracked |
| No payload visibility | Every request payload saved |

### ✅ Better Error Diagnosis

| Error Type | Information Captured |
|------------|---------------------|
| HTTP 401 | Authentication headers, API key validity |
| HTTP 400 | Exact validation error, row number, field name |
| HTTP 500 | Server error details, timeout duration |
| Network Error | Connection details, timeout settings |

### ✅ Comprehensive Reporting

**Dashboard Features:**
- 📊 Real-time statistics
- 🔍 Advanced filtering (status, type, date)
- 📋 Detailed drill-down views
- 💾 Export to text reports
- 🔄 Automatic refresh
- 📱 Responsive design

## Database Location

All logs are stored in:
```
/home/runner/work/miss-receipt-template/miss-receipt-template/upload_logs.db
```

**Tables:**
- `upload_logs` - Main upload tracking
- `api_logs` - API request/response details

## Next Steps

1. **Configure API Credentials**
   - Set Oracle Fusion API endpoint
   - Add authentication token
   - Test connection

2. **Enable Auto-Upload**
   - Integrate with receipt generation flow
   - Automatically upload after generation
   - Track status in dashboard

3. **Set Up Monitoring**
   - Regular checks of failed uploads
   - Email notifications (future feature)
   - Automated retry for transient failures

4. **Review and Optimize**
   - Analyze common failure patterns
   - Improve error handling
   - Optimize API payload format

## Support

- **Dashboard**: http://localhost:5000/upload-logs
- **API Docs**: See UPLOAD_LOG_MANAGEMENT_GUIDE.md
- **Database**: SQLite at `upload_logs.db`
