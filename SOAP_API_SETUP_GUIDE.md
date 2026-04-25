# Oracle Fusion SOAP/REST API Setup Guide

## 🔍 Problem Diagnosis

Your SOAP/REST APIs were not working due to **3 critical issues**:

### Issue #1: Missing Dependencies
- ❌ `requests` library was NOT in requirements.txt
- ❌ `zeep` library for SOAP was NOT installed
- ❌ `python-dotenv` for environment configuration was NOT installed

### Issue #2: Mock Mode Always Enabled
- The `upload_manager.py` had `self.mock_mode = True` hardcoded
- All API calls were going to mock functions, not real Oracle Fusion
- No actual HTTP requests were being made

### Issue #3: No Configuration
- No `.env` file for credentials
- No API endpoint configuration
- Placeholder URLs still in place

## ✅ What Has Been Fixed

### 1. Dependencies Added
Updated `requirements.txt` with:
```
requests>=2.31.0      # For REST API calls
zeep>=4.2.1           # For SOAP API calls
python-dotenv>=1.0.0  # For environment configuration
```

### 2. REST API Client Implemented
- Full implementation in `upload_manager.py`
- Proper authentication with HTTPBasicAuth
- Comprehensive error handling (timeout, connection errors, etc.)
- Environment-based configuration
- Automatic mock mode detection

### 3. SOAP Client Created
New file: `oracle_soap_client.py`
- Full SOAP client using `zeep` library
- Support for Receivables and Cash Management services
- WSDL-based service discovery
- Built-in testing functionality

### 4. Configuration System
- Created `.env.template` with all required settings
- Automatic environment variable loading
- Clear error messages when misconfigured
- Safe defaults for development

## 🚀 Quick Start - Enable Real API Calls

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Credentials
```bash
# Copy the template
cp .env.template .env

# Edit .env and add your credentials
nano .env  # or use any text editor
```

### Step 3: Update .env File
```env
# Set your actual Oracle Fusion instance URL
ORACLE_API_ENDPOINT=https://YOUR-INSTANCE.fa.oracle.com/fscmRestApi/resources/11.13.18.05

# Add your credentials
ORACLE_API_USERNAME=your-username
ORACLE_API_PASSWORD=your-password

# Disable mock mode to use real API
API_MOCK_MODE=false
```

### Step 4: Restart Application
```bash
python app.py
```

You should now see:
```
================================================================================
✅ UPLOAD MANAGER CONFIGURED FOR REAL API CALLS
Endpoint: https://YOUR-INSTANCE.fa.oracle.com/fscmRestApi/...
Username: your-username
Timeout: 30s
================================================================================
```

## 📝 Configuration Reference

### REST API Configuration (.env)
```env
# REST API Endpoint (required)
ORACLE_API_ENDPOINT=https://your-instance.fa.oracle.com/fscmRestApi/resources/11.13.18.05

# Credentials (required)
ORACLE_API_USERNAME=your-username
ORACLE_API_PASSWORD=your-password

# Optional: API behavior
API_MOCK_MODE=false           # Set to false for real calls
API_TIMEOUT=30                # Request timeout in seconds
API_DEBUG_LOGGING=true        # Enable detailed logging
API_MAX_RETRIES=3            # Max retry attempts
```

### SOAP API Configuration (.env)
```env
# SOAP WSDL URLs
ORACLE_SOAP_WSDL_RECEIVABLES=https://your-instance.fa.oracle.com/fscmService/ReceivablesInvoicesService?WSDL
ORACLE_SOAP_WSDL_CASHMANAGEMENT=https://your-instance.fa.oracle.com/fscmService/CashManagementService?WSDL

# SOAP Credentials
ORACLE_SOAP_USERNAME=your-username
ORACLE_SOAP_PASSWORD=your-password
```

## 🧪 Testing API Connectivity

### Test REST API
```bash
# Start the application
python app.py

# Check the startup messages for configuration status
# Look for "✅ UPLOAD MANAGER CONFIGURED FOR REAL API CALLS"
```

### Test SOAP API
```bash
# Run the SOAP client test
python oracle_soap_client.py
```

Expected output:
```
================================================================================
ORACLE FUSION SOAP CLIENT - CONNECTION TEST
================================================================================

✅ Client is configured
Username: your-username
WSDL: https://your-instance.fa.oracle.com/fscmService/...

📡 Fetching available operations...
✅ Found XX operations

Available operations:
  - createReceipt
  - updateReceipt
  - findReceipts
  ...

================================================================================
✅ SOAP CLIENT TEST PASSED
================================================================================
```

## 🔧 Troubleshooting

### Mock Mode Still Enabled?

If you see this message:
```
⚠️  UPLOAD MANAGER RUNNING IN MOCK MODE
```

Check the reason printed below it:

**"Reason: requests library not installed"**
```bash
pip install requests
```

**"Reason: Oracle Fusion credentials not configured"**
- Make sure `.env` file exists
- Verify `ORACLE_API_USERNAME` and `ORACLE_API_PASSWORD` are set

**"Reason: Oracle Fusion API endpoint not configured"**
- Update `ORACLE_API_ENDPOINT` in `.env`
- Replace "your-oracle-instance" with actual URL

**"Reason: API_MOCK_MODE=true in .env file"**
- Change `API_MOCK_MODE=false` in `.env`

### Connection Errors

**Timeout errors:**
- Increase `API_TIMEOUT` in `.env` (default: 30 seconds)
- Check network connectivity to Oracle Fusion

**Authentication errors (401):**
- Verify username and password in `.env`
- Check if account has necessary permissions

**SSL/Certificate errors:**
- Ensure you're using correct HTTPS URL
- Check if corporate proxy/firewall is blocking

## 📊 How It Works

### REST API Flow
```
upload_manager.py
    ↓
1. Load credentials from .env
2. Check if properly configured
3. If configured → Make real HTTP request
4. If not → Use mock mode
    ↓
Oracle Fusion REST API
    ↓
Response logged to database
```

### SOAP API Flow
```
oracle_soap_client.py
    ↓
1. Load WSDL from Oracle Fusion
2. Create SOAP client with zeep
3. Authenticate with credentials
4. Call SOAP operations
    ↓
Oracle Fusion SOAP Services
```

## 🔒 Security Notes

- ⚠️ **NEVER commit .env file** - It's already in .gitignore
- ✅ Use environment variables in production
- ✅ Rotate credentials regularly
- ✅ Use service accounts with minimal permissions
- ✅ Enable SSL certificate verification (default: on)

## 📦 API Endpoints Used

### REST API Endpoints
- **Cash Receipts**: `/receivables/cashReceipts`
- **Customers**: `/receivables/customers`
- **Invoices**: `/receivables/invoices`

### SOAP Services
- **Receivables Invoice Service**: `ReceivablesInvoicesService`
- **Cash Management Service**: `CashManagementService`

## 🎯 Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Copy template: `cp .env.template .env`
3. ✅ Configure credentials in `.env`
4. ✅ Set `API_MOCK_MODE=false`
5. ✅ Test connectivity: `python oracle_soap_client.py`
6. ✅ Restart app: `python app.py`
7. ✅ Try uploading a receipt file

## 📞 Support

If APIs still not working after following this guide:

1. Check startup messages for specific error
2. Enable debug logging: `API_DEBUG_LOGGING=true` in `.env`
3. Test Oracle Fusion connectivity from your network
4. Verify Oracle Fusion instance URL is correct
5. Check upload logs in the web UI for detailed error messages

## 🔗 Related Files

- `upload_manager.py` - REST API client implementation
- `oracle_soap_client.py` - SOAP API client implementation
- `.env.template` - Configuration template
- `requirements.txt` - Python dependencies
- `upload_logger.py` - API call logging
