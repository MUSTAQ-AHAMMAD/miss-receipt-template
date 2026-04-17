"""
================================================================================
PDF REPORT GENERATOR
================================================================================
Generate PDF reports from verification reports and data analysis
================================================================================
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import io


def generate_pdf_from_text(text_content: str, title: str = "Report") -> bytes:
    """
    Generate HTML content from text for browser-based PDF conversion.
    
    Note: This function returns HTML encoded as UTF-8 bytes, not actual PDF bytes.
    The HTML is designed to be displayed in a browser where users can use
    the browser's "Print to PDF" function to generate the final PDF.
    
    Args:
        text_content: The text content to convert to HTML
        title: Title for the HTML document
        
    Returns:
        HTML content as UTF-8 encoded bytes (not actual PDF)
    """
    # Create HTML wrapper for the text content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Courier New', monospace;
                margin: 2cm;
                font-size: 10pt;
                line-height: 1.4;
                color: #333;
            }}
            h1 {{
                color: #2563eb;
                border-bottom: 2px solid #2563eb;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #2563eb;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 10px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #ccc;
                text-align: center;
                font-size: 8pt;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{title}</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <pre>{text_content}</pre>
        <div class="footer">
            <p>Oracle Fusion Financial Integration - Report Generator</p>
        </div>
    </body>
    </html>
    """
    
    return html_content.encode('utf-8')


def generate_invoice_summary_pdf(
    ar_invoice_path: str,
    metadata_path: Optional[str] = None,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate an HTML summary report from AR Invoice data.
    
    Note: Returns HTML (not actual PDF) for browser-based PDF conversion.
    
    Args:
        ar_invoice_path: Path to AR Invoice CSV
        metadata_path: Optional path to metadata CSV
        output_path: Optional output path to save HTML
        
    Returns:
        HTML content as UTF-8 encoded bytes (not actual PDF)
    """
    import pandas as pd
    
    # Load AR Invoice
    ar_df = pd.read_csv(ar_invoice_path, encoding="utf-8-sig")
    
    # Generate summary statistics
    summary_lines = []
    summary_lines.append("="*80)
    summary_lines.append("AR INVOICE SUMMARY REPORT")
    summary_lines.append("="*80)
    summary_lines.append("")
    summary_lines.append(f"File: {Path(ar_invoice_path).name}")
    summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("")
    summary_lines.append("OVERVIEW")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Total Rows:              {len(ar_df):,}")
    summary_lines.append(f"Total Amount:            {ar_df['Transaction Line Amount'].sum():,.2f} SAR")
    summary_lines.append(f"Unique Transactions:     {ar_df['Transaction Number'].nunique():,}")
    summary_lines.append(f"Unique Invoices:         {ar_df['Sales Order Number'].nunique():,}")
    summary_lines.append("")
    
    # Transaction breakdown by date
    summary_lines.append("TRANSACTION BREAKDOWN BY DATE")
    summary_lines.append("-" * 80)
    date_summary = ar_df.groupby('Transaction Date').agg({
        'Transaction Line Amount': 'sum',
        'Transaction Number': 'nunique',
        'Sales Order Number': 'nunique'
    }).reset_index()
    date_summary.columns = ['Date', 'Total Amount', 'Transactions', 'Invoices']
    
    summary_lines.append(f"{'Date':<20} {'Amount (SAR)':>18} {'Transactions':>15} {'Invoices':>12}")
    summary_lines.append("-" * 80)
    for _, row in date_summary.iterrows():
        summary_lines.append(
            f"{row['Date']:<20} {row['Total Amount']:>18,.2f} "
            f"{row['Transactions']:>15} {row['Invoices']:>12}"
        )
    summary_lines.append("-" * 80)
    summary_lines.append(
        f"{'TOTAL':<20} {date_summary['Total Amount'].sum():>18,.2f} "
        f"{date_summary['Transactions'].sum():>15} {date_summary['Invoices'].sum():>12}"
    )
    summary_lines.append("")
    
    # Store breakdown
    summary_lines.append("STORE BREAKDOWN")
    summary_lines.append("-" * 80)
    store_summary = ar_df.groupby('Bill-to Customer Account Number').agg({
        'Transaction Line Amount': 'sum',
        'Transaction Number': 'nunique',
        'Sales Order Number': 'nunique'
    }).reset_index()
    store_summary.columns = ['Store', 'Total Amount', 'Transactions', 'Invoices']
    store_summary = store_summary.sort_values('Total Amount', ascending=False)
    
    summary_lines.append(f"{'Store':<30} {'Amount (SAR)':>18} {'Transactions':>15} {'Invoices':>12}")
    summary_lines.append("-" * 80)
    for _, row in store_summary.head(20).iterrows():
        summary_lines.append(
            f"{str(row['Store'])[:30]:<30} {row['Total Amount']:>18,.2f} "
            f"{row['Transactions']:>15} {row['Invoices']:>12}"
        )
    
    summary_lines.append("")
    
    # Discount items analysis
    discount_items = ar_df[
        (ar_df["Memo Line Name"] == "Discount Item") |
        (ar_df["Inventory Item Number"] == "")
    ]
    regular_items = ar_df[
        (ar_df["Memo Line Name"] != "Discount Item") &
        (ar_df["Inventory Item Number"] != "")
    ]
    
    summary_lines.append("DISCOUNT ITEMS ANALYSIS")
    summary_lines.append("-" * 80)
    summary_lines.append(f"Discount Lines:          {len(discount_items):,}")
    summary_lines.append(f"Discount Amount:         {discount_items['Transaction Line Amount'].sum():,.2f} SAR")
    summary_lines.append(f"Regular Lines:           {len(regular_items):,}")
    summary_lines.append(f"Regular Amount:          {regular_items['Transaction Line Amount'].sum():,.2f} SAR")
    if len(ar_df) > 0:
        discount_pct = (len(discount_items) / len(ar_df) * 100)
        summary_lines.append(f"Discount Percentage:     {discount_pct:.2f}%")
    
    summary_text = "\n".join(summary_lines)
    
    # Generate HTML (not actual PDF)
    html_bytes = generate_pdf_from_text(summary_text, "AR Invoice Summary Report")
    
    # Save if output path provided
    if output_path:
        Path(output_path).write_bytes(html_bytes)
    
    return html_bytes


def generate_comparison_pdf(
    ar_total: float,
    input_total: float,
    ar_invoice_path: str,
    date_breakdown: Optional[Dict] = None,
    output_path: Optional[str] = None
) -> bytes:
    """
    Generate HTML comparing AR Invoice totals with input sheet totals.
    
    Note: Returns HTML (not actual PDF) for browser-based PDF conversion.
    
    Args:
        ar_total: Total from AR Invoice
        input_total: Total from input sheet
        ar_invoice_path: Path to AR Invoice file
        date_breakdown: Optional dictionary with date-wise breakdown
        output_path: Optional output path to save HTML
        
    Returns:
        HTML content as UTF-8 encoded bytes (not actual PDF)
    """
    summary_lines = []
    summary_lines.append("="*80)
    summary_lines.append("AR INVOICE vs INPUT SHEET COMPARISON REPORT")
    summary_lines.append("="*80)
    summary_lines.append("")
    summary_lines.append(f"File: {Path(ar_invoice_path).name}")
    summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("")
    summary_lines.append("TOTAL COMPARISON")
    summary_lines.append("-" * 80)
    summary_lines.append(f"AR Invoice Total:        {ar_total:>20,.2f} SAR")
    summary_lines.append(f"Input Sheet Total:       {input_total:>20,.2f} SAR")
    summary_lines.append(f"Difference:              {abs(ar_total - input_total):>20,.2f} SAR")
    
    match_threshold = 0.01
    if abs(ar_total - input_total) < match_threshold:
        summary_lines.append(f"Status:                  {'✓ MATCH':>26}")
    else:
        summary_lines.append(f"Status:                  {'⚠ MISMATCH':>26}")
    
    summary_lines.append("")
    
    if date_breakdown:
        summary_lines.append("DATE-WISE BREAKDOWN")
        summary_lines.append("-" * 80)
        summary_lines.append(f"{'Date':<20} {'AR Amount':>18} {'Input Amount':>18} {'Difference':>18}")
        summary_lines.append("-" * 80)
        
        for date, amounts in sorted(date_breakdown.items()):
            ar_amt = amounts.get('ar', 0)
            input_amt = amounts.get('input', 0)
            diff = abs(ar_amt - input_amt)
            summary_lines.append(
                f"{date:<20} {ar_amt:>18,.2f} {input_amt:>18,.2f} {diff:>18,.2f}"
            )
    
    summary_text = "\n".join(summary_lines)
    
    # Generate HTML (not actual PDF)
    html_bytes = generate_pdf_from_text(summary_text, "AR Invoice Comparison Report")
    
    # Save if output path provided
    if output_path:
        Path(output_path).write_bytes(html_bytes)
    
    return html_bytes
