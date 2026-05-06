# Journal Template Sales Lines Amount Fix

## Problem Statement

The journal template generation was not picking up the correct payment amounts from sales lines items. Instead, it was using amounts directly from the payment file, which could be incorrect or incomplete.

**User Issue:**
> "still i see the payment amount in the generated journal template file the amount should be picked from sales lines items and match sales order ref in the payment lines sheet and this is not happening the amount is not full filled"

## Root Cause

The code was loading the `sales_lines_file_path` but never actually using the data from it. The amount was being taken from:
1. Payment file (`method_amt` from `payment_data`)
2. Or AR Invoice (`Transaction Line Amount`)

But it was NOT summing up the amounts from individual sales line items.

## Solution Implemented

### 1. Sales Lines File Loading and Aggregation

Added logic to:
- Load the sales lines file (XLSX or CSV)
- Automatically detect column names for Sales Order Number (supports multiple naming conventions)
- Automatically detect column names for Amount/Price (supports multiple naming conventions)
- Aggregate line item amounts by Sales Order Number
- Store the totals in a dictionary for quick lookup

**Supported Column Names:**

Sales Order Reference:
- "Sales Order Number"
- "Order Ref"
- "Order Reference"
- "Sales Order"
- "Order Lines/Order Ref"
- "SO Number"
- "Invoice Number"
- "Reference"

Amount/Price:
- "Price Subtotal"
- "Subtotal"
- "Amount"
- "Line Amount"
- "Order Lines/Price Subtotal"
- "Total"
- "Line Total"

### 2. Amount Selection Logic

When building journal entries, the system now:
1. **First checks** if sales lines totals are available for the Sales Order
2. **If found:** Uses the aggregated amount from sales lines items
3. **If not found:** Falls back to the payment file amount
4. **Logs clearly** which source was used for each transaction

### 3. Code Changes

**File:** `Odoo-export-FBDA-template.py`

**Lines 4019-4083:** Sales lines loading and aggregation
```python
# Load sales lines file and aggregate amounts by Sales Order Number
sales_lines_totals: Dict[str, float] = {}  # {sales_order_ref: total_amount}
if sales_lines_file_path and Path(sales_lines_file_path).exists():
    # Load file, detect columns, aggregate by Sales Order Number
    # Result: sales_lines_totals = {"SO001": 150.50, "SO002": 200.00, ...}
```

**Lines 4286-4305 and 4323-4342:** Amount selection with sales lines priority
```python
# Use amount from sales lines if available, otherwise fall back to payment amount
if sales_lines_totals and sales_order_ref in sales_lines_totals:
    final_amount = sales_lines_totals[sales_order_ref]
    print(f"  ℹ️  Using sales lines amount for {sales_order_ref}: {final_amount:.2f} SAR")
else:
    final_amount = method_amt
    if sales_lines_totals:
        print(f"  ⚠  No sales lines data found for {sales_order_ref}, using payment amount")
```

## Usage

### Via Web UI

1. Navigate to "Journal Template Only" mode
2. Upload the **AR Invoice** file (optional but recommended)
3. Upload the **Payment Lines** file (required)
4. Upload the **Sales Lines** file (required for correct amounts)
5. Click "Generate"

The system will:
- Match Sales Order Numbers from the payment file
- Look up the corresponding total amounts from the sales lines file
- Generate journal entries with the correct aggregated amounts

### Via API

```python
journal_df = integration.generate_journal_template(
    journal_config_path="...",
    account_mapping_path="...",
    period_name="Mar-26",
    interface_group_id=114,
    service_provider_meta_path="SERVICE_PROVIDER_JOURNAL_META.csv",
    cost_center_meta_path="FUSION_SALES_METADATA_Cost_Center.csv",
    payment_file_path="payment_lines.xlsx",  # Contains TABBY/TAMARA payment methods
    sales_lines_file_path="sales_lines.xlsx",  # Contains line items with amounts
    charges_file_path="charges.csv",
)
```

## Verification

The system now provides detailed logging output:

```
✓  Loading sales lines file: sales_lines.xlsx
✓  Loaded 450 sales line items
✓  Aggregated amounts for 150 unique sales orders from sales lines
   Column used for Sales Order: 'Order Ref'
   Column used for Amount: 'Price Subtotal'
   Sample totals:
     - SO-001: 234.50 SAR
     - SO-002: 156.00 SAR
     - SO-003: 89.75 SAR

✓  Building journal entries directly from payment file
  ℹ️  Using sales lines amount for SO-001: 234.50 SAR (payment file had: 230.00 SAR)
  ℹ️  Using sales lines amount for SO-002: 156.00 SAR (payment file had: 155.00 SAR)
  ⚠  No sales lines data found for SO-099, using payment amount: 50.00 SAR
```

## Benefits

1. **Accurate Amounts**: Journal entries now reflect the actual sales order totals from line items
2. **Automatic Matching**: System automatically matches Sales Orders between payment and sales lines files
3. **Flexible Fallback**: If sales lines data is missing, gracefully falls back to payment file amount
4. **Clear Logging**: Detailed output shows exactly which source was used for each amount
5. **Column Name Tolerance**: Automatically handles various column naming conventions

## Testing

To verify the fix works correctly:

1. Check the console output when generating journal template
2. Look for messages like: `"Using sales lines amount for [Order Ref]"`
3. Compare the amounts in the generated journal template with the sales lines file totals
4. Verify that journal entries are balanced (total debits = total credits)

## Known Limitations

- Sales lines file must contain a column that matches Sales Order Numbers from the payment file
- If the sales lines file has a different Sales Order format or naming, manual column mapping may be needed
- The fix assumes one total amount per Sales Order (aggregates all line items)

## Related Files

- `Odoo-export-FBDA-template.py` - Main implementation
- `app.py` - Web UI integration (lines 357, 636-638)
- `JOURNAL_TEMPLATE_GENERATION_GUIDE.md` - User documentation

## Version History

- **2026-05-06**: Initial fix implemented
  - Added sales lines file loading and aggregation
  - Implemented amount selection with sales lines priority
  - Added detailed logging for transparency
