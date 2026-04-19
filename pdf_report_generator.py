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
    import html

    # Escape HTML special characters to prevent XSS
    escaped_content = html.escape(text_content)
    escaped_title = html.escape(title)

    # Create HTML wrapper for the text content with enhanced professional styling
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{escaped_title}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                margin: 0;
                padding: 40px;
                font-size: 11pt;
                line-height: 1.6;
                color: #1a1a1a;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }}

            .page {{
                max-width: 900px;
                margin: 0 auto;
                background: white;
                padding: 50px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                border-radius: 8px;
            }}

            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding: 40px 30px;
                background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
                color: white;
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            }}

            h1 {{
                font-size: 32px;
                font-weight: 700;
                margin-bottom: 12px;
                letter-spacing: -0.5px;
                text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}

            .timestamp {{
                font-size: 14px;
                opacity: 0.95;
                font-weight: 300;
                letter-spacing: 0.5px;
            }}

            pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                background: linear-gradient(to right, #fafbfc 0%, #f5f7fa 100%);
                padding: 30px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                font-family: 'SF Mono', 'Monaco', 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                line-height: 1.5;
                color: #202124;
                box-shadow: inset 0 2px 8px rgba(0,0,0,0.05);
            }}

            .footer {{
                margin-top: 40px;
                padding: 30px;
                border-top: 2px solid #e1e8ed;
                text-align: center;
                background: linear-gradient(to right, #fafbfc 0%, #f5f7fa 100%);
                border-radius: 8px;
            }}

            .footer p {{
                font-size: 10pt;
                color: #5f6368;
                margin: 8px 0;
                font-weight: 500;
            }}

            .footer strong {{
                color: #202124;
                font-weight: 700;
            }}

            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}

                .page {{
                    box-shadow: none;
                    padding: 20px;
                    max-width: 100%;
                }}

                .header {{
                    background: #0f2027 !important;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }}

                pre {{
                    background: #fafbfc !important;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="page">
            <div class="header">
                <h1>{escaped_title}</h1>
                <p class="timestamp">Generated on {datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p')}</p>
            </div>
            <pre>{escaped_content}</pre>
            <div class="footer">
                <p><strong>Oracle Fusion Financial Integration</strong></p>
                <p>Professional Report Generator • Enterprise Edition</p>
                <p>For questions or support, contact your system administrator</p>
            </div>
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
