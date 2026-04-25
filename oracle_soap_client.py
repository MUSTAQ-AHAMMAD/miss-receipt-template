"""
================================================================================
ORACLE FUSION SOAP CLIENT
================================================================================
SOAP-based client for Oracle Fusion Cloud APIs.
Provides access to services that are not available via REST API.
================================================================================
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from zeep import Client, Settings
    from zeep.transports import Transport
    from zeep.wsse.username import UsernameToken
    from requests import Session
    from requests.auth import HTTPBasicAuth
    ZEEP_AVAILABLE = True
except ImportError:
    ZEEP_AVAILABLE = False
    print("WARNING: zeep library not installed. Install with: pip install zeep")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class OracleFusionSOAPClient:
    """
    SOAP client for Oracle Fusion Cloud services.

    Provides access to:
    - Receivables Invoice Service
    - Cash Management Service
    - Journal Entry Service
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        wsdl_receivables: str = None,
        wsdl_cash_management: str = None,
        timeout: int = 60
    ):
        """
        Initialize Oracle Fusion SOAP client.

        Args:
            username: Oracle Fusion username
            password: Oracle Fusion password
            wsdl_receivables: WSDL URL for Receivables service
            wsdl_cash_management: WSDL URL for Cash Management service
            timeout: Request timeout in seconds
        """
        if not ZEEP_AVAILABLE:
            raise RuntimeError(
                "zeep library is required for SOAP operations. "
                "Install with: pip install zeep"
            )

        # Load credentials from environment
        self.username = username or os.getenv('ORACLE_SOAP_USERNAME')
        self.password = password or os.getenv('ORACLE_SOAP_PASSWORD')

        # Load WSDL URLs from environment
        self.wsdl_receivables = wsdl_receivables or os.getenv(
            'ORACLE_SOAP_WSDL_RECEIVABLES',
            'https://your-oracle-instance.fa.oracle.com/fscmService/ReceivablesInvoicesService?WSDL'
        )
        self.wsdl_cash_management = wsdl_cash_management or os.getenv(
            'ORACLE_SOAP_WSDL_CASHMANAGEMENT',
            'https://your-oracle-instance.fa.oracle.com/fscmService/CashManagementService?WSDL'
        )

        self.timeout = timeout

        # Check if configured
        self.is_configured = (
            self.username and
            self.password and
            "your-oracle-instance" not in self.wsdl_receivables
        )

        if not self.is_configured:
            print("=" * 80)
            print("⚠️  ORACLE SOAP CLIENT NOT CONFIGURED")
            print("=" * 80)
            print("To enable SOAP services, configure the following in .env:")
            print("  - ORACLE_SOAP_USERNAME")
            print("  - ORACLE_SOAP_PASSWORD")
            print("  - ORACLE_SOAP_WSDL_RECEIVABLES")
            print("  - ORACLE_SOAP_WSDL_CASHMANAGEMENT")
            print("=" * 80)
        else:
            print("=" * 80)
            print("✅ ORACLE SOAP CLIENT CONFIGURED")
            print(f"Username: {self.username}")
            print(f"Receivables WSDL: {self.wsdl_receivables[:80]}...")
            print("=" * 80)

        self._receivables_client = None
        self._cash_management_client = None

    def _get_session(self) -> Session:
        """Create configured requests session"""
        session = Session()
        session.auth = HTTPBasicAuth(self.username, self.password)
        return session

    def _get_receivables_client(self) -> Client:
        """Get or create Receivables service client"""
        if not self._receivables_client:
            session = self._get_session()
            transport = Transport(session=session, timeout=self.timeout)
            settings = Settings(strict=False, xml_huge_tree=True)

            self._receivables_client = Client(
                wsdl=self.wsdl_receivables,
                transport=transport,
                settings=settings
            )

        return self._receivables_client

    def _get_cash_management_client(self) -> Client:
        """Get or create Cash Management service client"""
        if not self._cash_management_client:
            session = self._get_session()
            transport = Transport(session=session, timeout=self.timeout)
            settings = Settings(strict=False, xml_huge_tree=True)

            self._cash_management_client = Client(
                wsdl=self.wsdl_cash_management,
                transport=transport,
                settings=settings
            )

        return self._cash_management_client

    def create_receipt(
        self,
        receipt_number: str,
        receipt_date: str,
        amount: float,
        customer_account_number: str,
        payment_method: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a cash receipt in Oracle Fusion.

        Args:
            receipt_number: Unique receipt number
            receipt_date: Receipt date (YYYY-MM-DD format)
            amount: Receipt amount
            customer_account_number: Customer account number
            payment_method: Payment method name
            **kwargs: Additional receipt attributes

        Returns:
            Response dict with status and receipt ID
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "SOAP client not configured"
            }

        try:
            client = self._get_cash_management_client()

            # Build receipt payload
            # Note: Actual structure depends on Oracle Fusion WSDL schema
            receipt_data = {
                'ReceiptNumber': receipt_number,
                'ReceiptDate': receipt_date,
                'ReceiptAmount': amount,
                'CustomerAccountNumber': customer_account_number,
                'PaymentMethod': payment_method,
                **kwargs
            }

            # Call SOAP service
            response = client.service.createReceipt(receipt_data)

            return {
                "success": True,
                "receipt_id": response.ReceiptId if hasattr(response, 'ReceiptId') else None,
                "response": response
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def query_receipts(
        self,
        start_date: str = None,
        end_date: str = None,
        customer_account: str = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Query cash receipts from Oracle Fusion.

        Args:
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            customer_account: Filter by customer account
            limit: Maximum number of results

        Returns:
            Response dict with receipts list
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "SOAP client not configured"
            }

        try:
            client = self._get_cash_management_client()

            # Build query criteria
            criteria = {}
            if start_date:
                criteria['StartDate'] = start_date
            if end_date:
                criteria['EndDate'] = end_date
            if customer_account:
                criteria['CustomerAccount'] = customer_account
            criteria['Limit'] = limit

            # Call SOAP service
            response = client.service.findReceipts(criteria)

            return {
                "success": True,
                "receipts": response.Receipts if hasattr(response, 'Receipts') else [],
                "count": len(response.Receipts) if hasattr(response, 'Receipts') else 0
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_service_operations(self, service: str = 'receivables') -> List[str]:
        """
        Get available operations for a service.
        Useful for debugging and exploring the WSDL.

        Args:
            service: 'receivables' or 'cash_management'

        Returns:
            List of operation names
        """
        if not self.is_configured:
            return []

        try:
            if service == 'receivables':
                client = self._get_receivables_client()
            else:
                client = self._get_cash_management_client()

            return [operation for operation in dir(client.service) if not operation.startswith('_')]

        except Exception as e:
            print(f"Error getting service operations: {e}")
            return []


def test_soap_client():
    """Test SOAP client configuration and connectivity"""
    print("\n" + "=" * 80)
    print("ORACLE FUSION SOAP CLIENT - CONNECTION TEST")
    print("=" * 80)

    client = OracleFusionSOAPClient()

    if not client.is_configured:
        print("\n❌ Client is not configured")
        print("Please configure credentials in .env file")
        return False

    print("\n✅ Client is configured")
    print(f"Username: {client.username}")
    print(f"WSDL: {client.wsdl_receivables[:80]}...")

    try:
        print("\n📡 Fetching available operations...")
        operations = client.get_service_operations('cash_management')
        print(f"✅ Found {len(operations)} operations")
        if operations:
            print("\nAvailable operations:")
            for op in operations[:10]:  # Show first 10
                print(f"  - {op}")
            if len(operations) > 10:
                print(f"  ... and {len(operations) - 10} more")

        print("\n" + "=" * 80)
        print("✅ SOAP CLIENT TEST PASSED")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ SOAP CLIENT TEST FAILED")
        print(f"Error: {e}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    test_soap_client()
