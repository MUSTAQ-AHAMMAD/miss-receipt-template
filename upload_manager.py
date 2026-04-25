"""
================================================================================
UPLOAD MANAGER - Oracle Fusion Receipt Upload Handler
================================================================================
Handles uploading receipt files to Oracle Fusion with detailed logging,
retry logic, and comprehensive error reporting.
================================================================================
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

try:
    import requests
    from requests.auth import HTTPBasicAuth
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests library not installed. Install with: pip install requests")

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("WARNING: python-dotenv not installed. Install with: pip install python-dotenv")

from upload_logger import UploadLogger


class UploadManager:
    """
    Manages the upload of receipt files to Oracle Fusion API.
    Provides detailed logging, error handling, and retry logic.
    """

    def __init__(
        self,
        api_endpoint: str = None,
        api_username: str = None,
        api_password: str = None,
        logger: UploadLogger = None
    ):
        """
        Initialize the upload manager.

        Args:
            api_endpoint: Oracle Fusion API endpoint URL
            api_username: Oracle Fusion username
            api_password: Oracle Fusion password
            logger: UploadLogger instance (creates new one if None)
        """
        # Load from environment variables if not provided
        self.api_endpoint = api_endpoint or os.getenv(
            'ORACLE_API_ENDPOINT',
            "https://your-oracle-instance.fa.oracle.com/fscmRestApi/resources/11.13.18.05"
        )
        self.api_username = api_username or os.getenv('ORACLE_API_USERNAME')
        self.api_password = api_password or os.getenv('ORACLE_API_PASSWORD')
        self.logger = logger or UploadLogger()

        # Configuration from environment
        self.timeout = int(os.getenv('API_TIMEOUT', '30'))
        self.debug_logging = os.getenv('API_DEBUG_LOGGING', 'false').lower() == 'true'

        # Determine if we should use mock mode
        # Mock mode is enabled if:
        # 1. API_MOCK_MODE environment variable is explicitly set to true, OR
        # 2. requests library is not available, OR
        # 3. No credentials are configured
        env_mock_mode = os.getenv('API_MOCK_MODE', 'true').lower() == 'true'
        self.mock_mode = (
            env_mock_mode or
            not REQUESTS_AVAILABLE or
            not self.api_username or
            not self.api_password or
            "your-oracle-instance" in self.api_endpoint
        )

        if self.mock_mode:
            print("=" * 80)
            print("⚠️  UPLOAD MANAGER RUNNING IN MOCK MODE")
            print("=" * 80)
            if not REQUESTS_AVAILABLE:
                print("Reason: requests library not installed")
                print("Fix: pip install requests")
            elif not self.api_username or not self.api_password:
                print("Reason: Oracle Fusion credentials not configured")
                print("Fix: Set ORACLE_API_USERNAME and ORACLE_API_PASSWORD in .env file")
            elif "your-oracle-instance" in self.api_endpoint:
                print("Reason: Oracle Fusion API endpoint not configured")
                print("Fix: Set ORACLE_API_ENDPOINT in .env file")
            else:
                print("Reason: API_MOCK_MODE=true in .env file")
                print("Fix: Set API_MOCK_MODE=false in .env file")
            print("=" * 80)
        else:
            print("=" * 80)
            print("✅ UPLOAD MANAGER CONFIGURED FOR REAL API CALLS")
            print(f"Endpoint: {self.api_endpoint}")
            print(f"Username: {self.api_username}")
            print(f"Timeout: {self.timeout}s")
            print("=" * 80)

    def upload_receipt_file(
        self,
        file_path: str,
        receipt_type: str,
        session_id: str = None,
        max_retries: int = 3
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Upload a single receipt file to Oracle Fusion.

        Args:
            file_path: Path to the receipt CSV file
            receipt_type: "STANDARD" or "MISC"
            session_id: Optional session ID for tracking
            max_retries: Maximum number of retry attempts

        Returns:
            (success, error_message, upload_id)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return False, f"File not found: {file_path}", None

        # Read file to get metadata
        try:
            df = pd.read_csv(file_path)
            row_count = len(df)

            # Extract metadata based on receipt type
            if receipt_type == "STANDARD":
                amount_total = df["Amount"].sum() if "Amount" in df.columns else 0
                payment_method = self._extract_payment_method(file_path.name)
                store_name = None
                date_range = None
            else:  # MISC
                amount_total = df["Amount"].sum() if "Amount" in df.columns else 0
                payment_method = None
                store_name = None
                date_range = None

        except Exception as e:
            return False, f"Error reading file: {str(e)}", None

        # Log upload start
        upload_id = self.logger.log_upload_start(
            filename=file_path.name,
            receipt_type=receipt_type,
            session_id=session_id,
            file_size=file_path.stat().st_size,
            row_count=row_count,
            amount_total=amount_total,
            payment_method=payment_method,
            store_name=store_name,
            date_range=date_range
        )

        # Attempt upload with retries
        for attempt in range(max_retries):
            try:
                success, error_msg, error_row = self._attempt_upload(
                    file_path, df, upload_id, receipt_type
                )

                if success:
                    self.logger.update_upload_status(upload_id, "SUCCESS")
                    return True, None, upload_id
                else:
                    # Log failure
                    is_retry = attempt < max_retries - 1
                    status = "PENDING" if is_retry else "FAILED"
                    self.logger.update_upload_status(
                        upload_id, status, error_msg, error_row, is_retry
                    )

                    if not is_retry:
                        return False, error_msg, upload_id

                    # Wait before retry
                    time.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                self.logger.update_upload_status(
                    upload_id, "FAILED", error_msg
                )
                return False, error_msg, upload_id

        return False, "Max retries exceeded", upload_id

    def _attempt_upload(
        self,
        file_path: Path,
        df: pd.DataFrame,
        upload_id: int,
        receipt_type: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Attempt to upload a receipt file to the API.

        Returns:
            (success, error_message, error_row)
        """
        # Prepare API request
        endpoint = f"{self.api_endpoint}/receivables/cashReceipts"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Convert CSV to API payload format
        payload = self._prepare_payload(df, receipt_type)

        # Log the API request
        api_log_id = self.logger.log_api_request(
            upload_id=upload_id,
            http_method="POST",
            api_endpoint=endpoint,
            request_headers=headers,
            request_payload=payload
        )

        # Make the actual API call
        start_time = time.time()

        if self.mock_mode:
            # Mock response for testing/development
            response_status, response_body = self._mock_api_call(payload)
        else:
            # Real API call to Oracle Fusion
            try:
                if self.debug_logging:
                    print(f"Making API call to: {endpoint}")
                    print(f"Payload size: {len(str(payload))} bytes")

                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    auth=HTTPBasicAuth(self.api_username, self.api_password),
                    timeout=self.timeout,
                    verify=True  # Verify SSL certificates
                )

                response_status = response.status_code

                try:
                    response_body = response.json()
                except Exception:
                    # If response is not JSON, use text
                    response_body = {"text": response.text}

                if self.debug_logging:
                    print(f"Response status: {response_status}")
                    print(f"Response: {response_body}")

            except requests.exceptions.Timeout:
                response_status = 408
                response_body = {"error": "Request timeout", "message": f"Request timed out after {self.timeout}s"}
            except requests.exceptions.ConnectionError as e:
                response_status = 503
                response_body = {"error": "Connection error", "message": f"Could not connect to Oracle Fusion: {str(e)}"}
            except requests.exceptions.RequestException as e:
                response_status = 500
                response_body = {"error": "Request error", "message": f"API request failed: {str(e)}"}
            except Exception as e:
                response_status = 500
                response_body = {"error": "Unexpected error", "message": str(e)}

        duration_ms = int((time.time() - start_time) * 1000)

        # Log the API response
        self.logger.log_api_response(
            api_log_id=api_log_id,
            response_status=response_status,
            response_headers={"Content-Type": "application/json"},
            response_body=response_body,
            duration_ms=duration_ms
        )

        # Evaluate response
        if response_status == 200 or response_status == 201:
            return True, None, None
        elif response_status == 401:
            return False, f"HTTP 401: Authentication failed", None
        elif response_status == 400:
            # Try to extract row number from error
            error_row = self._extract_error_row(response_body)
            error_msg = response_body.get('message', 'Bad Request') if isinstance(response_body, dict) else str(response_body)
            return False, f"HTTP 400: {error_msg}", error_row
        else:
            error_msg = response_body.get('message', 'Unknown error') if isinstance(response_body, dict) else str(response_body)
            return False, f"HTTP {response_status}: {error_msg}", None

    def _prepare_payload(self, df: pd.DataFrame, receipt_type: str) -> Dict:
        """Convert DataFrame to API payload format"""
        if receipt_type == "STANDARD":
            return {
                "receiptType": "STANDARD",
                "receipts": df.to_dict(orient='records'),
                "metadata": {
                    "totalRecords": len(df),
                    "totalAmount": float(df["Amount"].sum()) if "Amount" in df.columns else 0
                }
            }
        else:  # MISC
            return {
                "receiptType": "MISCELLANEOUS",
                "receipts": df.to_dict(orient='records'),
                "metadata": {
                    "totalRecords": len(df),
                    "totalAmount": float(df["Amount"].sum()) if "Amount" in df.columns else 0
                }
            }

    def _mock_api_call(self, payload: Dict) -> Tuple[int, Dict]:
        """Mock API response for testing (remove when real API is configured)"""
        # Simulate various responses for testing
        import random

        # 80% success rate in mock mode
        if random.random() < 0.8:
            return 201, {
                "status": "success",
                "message": "Receipts uploaded successfully",
                "processedRecords": payload['metadata']['totalRecords']
            }
        else:
            # Simulate occasional failures
            error_types = [
                (401, {"error": "Unauthorized", "message": "Invalid API credentials"}),
                (400, {"error": "ValidationError", "message": "Row 2: Invalid customer account number", "row": 2}),
                (500, {"error": "InternalServerError", "message": "Database connection timeout"})
            ]
            return random.choice(error_types)

    def _extract_payment_method(self, filename: str) -> Optional[str]:
        """Extract payment method from filename"""
        filename_upper = filename.upper()
        for method in ["CASH", "MADA", "VISA", "MASTERCARD"]:
            if method in filename_upper:
                return method.title()
        return None

    def _extract_error_row(self, response_body: any) -> Optional[int]:
        """Try to extract row number from error response"""
        if isinstance(response_body, dict):
            # Check common error fields
            if 'row' in response_body:
                return response_body['row']
            if 'rowNumber' in response_body:
                return response_body['rowNumber']
            if 'message' in response_body:
                # Try to parse "Row 2:" from message
                import re
                match = re.search(r'Row (\d+)', response_body['message'], re.IGNORECASE)
                if match:
                    return int(match.group(1))
        return None

    def upload_batch(
        self,
        receipt_dir: str,
        receipt_type: str = None,
        session_id: str = None
    ) -> Dict:
        """
        Upload multiple receipt files from a directory.

        Args:
            receipt_dir: Directory containing receipt CSV files
            receipt_type: "STANDARD", "MISC", or None (auto-detect)
            session_id: Optional session ID for tracking

        Returns:
            Summary dict with success/failure counts
        """
        receipt_dir = Path(receipt_dir)

        if not receipt_dir.exists():
            return {"error": f"Directory not found: {receipt_dir}"}

        # Find all CSV files
        csv_files = list(receipt_dir.glob("**/*.csv"))

        results = {
            "total": len(csv_files),
            "successful": 0,
            "failed": 0,
            "failures": []
        }

        for csv_file in csv_files:
            # Auto-detect type if not specified
            file_type = receipt_type
            if not file_type:
                file_type = "MISC" if "Misc" in str(csv_file) else "STANDARD"

            success, error_msg, upload_id = self.upload_receipt_file(
                str(csv_file),
                file_type,
                session_id
            )

            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["failures"].append({
                    "filename": csv_file.name,
                    "error": error_msg,
                    "upload_id": upload_id
                })

        return results
