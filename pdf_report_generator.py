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
    Generate an HTML summary report from AR Invoice data with proper visual design.

    Note: Returns HTML (not actual PDF) for browser-based PDF conversion.

    Args:
        ar_invoice_path: Path to AR Invoice CSV
        metadata_path: Optional path to metadata CSV
        output_path: Optional output path to save HTML

    Returns:
        HTML content as UTF-8 encoded bytes (not actual PDF)
    """
    import pandas as pd
    import html

    # Load AR Invoice
    ar_df = pd.read_csv(ar_invoice_path, encoding="utf-8-sig")

    # Calculate summary statistics
    total_rows = len(ar_df)
    total_amount = ar_df['Transaction Line Amount'].sum()
    unique_txns = ar_df['Transaction Number'].nunique()
    unique_invoices = ar_df['Sales Order Number'].nunique()

    # Transaction breakdown by date
    date_summary = ar_df.groupby('Transaction Date').agg({
        'Transaction Line Amount': 'sum',
        'Transaction Number': 'nunique',
        'Sales Order Number': 'nunique'
    }).reset_index()
    date_summary.columns = ['Date', 'Total Amount', 'Transactions', 'Invoices']

    # Store breakdown
    store_summary = ar_df.groupby('Bill-to Customer Account Number').agg({
        'Transaction Line Amount': 'sum',
        'Transaction Number': 'nunique',
        'Sales Order Number': 'nunique'
    }).reset_index()
    store_summary.columns = ['Store', 'Total Amount', 'Transactions', 'Invoices']
    store_summary = store_summary.sort_values('Total Amount', ascending=False).head(20)

    # Discount items analysis
    discount_items = ar_df[
        (ar_df["Memo Line Name"] == "Discount Item") |
        (ar_df["Inventory Item Number"] == "")
    ]
    regular_items = ar_df[
        (ar_df["Memo Line Name"] != "Discount Item") &
        (ar_df["Inventory Item Number"] != "")
    ]

    discount_count = len(discount_items)
    discount_amount = discount_items['Transaction Line Amount'].sum()
    regular_count = len(regular_items)
    regular_amount = regular_items['Transaction Line Amount'].sum()
    discount_pct = (discount_count / total_rows * 100) if total_rows > 0 else 0

    # Build professional HTML report
    escaped_filename = html.escape(Path(ar_invoice_path).name)
    timestamp = datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AR Invoice Summary Report</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px 20px;
                color: #1a202c;
                line-height: 1.6;
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}

            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 48px 40px;
                text-align: center;
            }}

            .header h1 {{
                font-size: 36px;
                font-weight: 800;
                margin-bottom: 12px;
                letter-spacing: -0.5px;
            }}

            .header .subtitle {{
                font-size: 16px;
                opacity: 0.95;
                font-weight: 400;
            }}

            .header .file-info {{
                margin-top: 24px;
                padding: 16px 24px;
                background: rgba(255,255,255,0.15);
                border-radius: 8px;
                display: inline-block;
                backdrop-filter: blur(10px);
            }}

            .header .file-info strong {{
                display: block;
                font-size: 14px;
                margin-bottom: 4px;
                opacity: 0.9;
            }}

            .content {{
                padding: 40px;
            }}

            .section {{
                margin-bottom: 48px;
            }}

            .section-title {{
                font-size: 24px;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 24px;
                padding-bottom: 12px;
                border-bottom: 3px solid #667eea;
                display: flex;
                align-items: center;
                gap: 12px;
            }}

            .section-icon {{
                font-size: 28px;
            }}

            .stat-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
                margin-bottom: 32px;
            }}

            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                transition: transform 0.2s;
            }}

            .stat-card:hover {{
                transform: translateY(-4px);
            }}

            .stat-label {{
                font-size: 13px;
                opacity: 0.9;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }}

            .stat-value {{
                font-size: 32px;
                font-weight: 800;
                letter-spacing: -1px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border-radius: 8px;
                overflow: hidden;
            }}

            thead {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}

            thead th {{
                padding: 16px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            thead th.number {{
                text-align: right;
            }}

            tbody tr {{
                border-bottom: 1px solid #e2e8f0;
                transition: background 0.2s;
            }}

            tbody tr:hover {{
                background: #f7fafc;
            }}

            tbody tr:last-child {{
                border-bottom: none;
            }}

            tbody td {{
                padding: 14px 16px;
                font-size: 14px;
            }}

            tbody td.number {{
                text-align: right;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 600;
                color: #2d3748;
            }}

            tbody td.store {{
                font-weight: 500;
                color: #4a5568;
            }}

            tfoot {{
                background: #f7fafc;
                font-weight: 700;
                border-top: 2px solid #667eea;
            }}

            tfoot td {{
                padding: 16px;
                font-size: 14px;
            }}

            tfoot td.number {{
                text-align: right;
                font-family: 'JetBrains Mono', monospace;
                color: #667eea;
            }}

            .discount-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 16px;
            }}

            .discount-item {{
                background: #f7fafc;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }}

            .discount-item .label {{
                font-size: 13px;
                color: #718096;
                font-weight: 500;
                margin-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            .discount-item .value {{
                font-size: 24px;
                font-weight: 700;
                color: #2d3748;
                font-family: 'JetBrains Mono', monospace;
            }}

            .footer {{
                background: #f7fafc;
                padding: 32px 40px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
            }}

            .footer p {{
                color: #718096;
                font-size: 14px;
                margin: 4px 0;
            }}

            .footer strong {{
                color: #2d3748;
                font-weight: 700;
            }}

            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}

                .container {{
                    box-shadow: none;
                }}

                .stat-card {{
                    break-inside: avoid;
                }}

                table {{
                    break-inside: avoid;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 AR Invoice Summary Report</h1>
                <p class="subtitle">Comprehensive Analysis & Breakdown</p>
                <div class="file-info">
                    <strong>📁 {escaped_filename}</strong>
                    {timestamp}
                </div>
            </div>

            <div class="content">
                <!-- Overview Stats -->
                <div class="section">
                    <h2 class="section-title">
                        <span class="section-icon">📈</span>
                        Overview Statistics
                    </h2>
                    <div class="stat-cards">
                        <div class="stat-card">
                            <div class="stat-label">Total Rows</div>
                            <div class="stat-value">{total_rows:,}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Total Amount</div>
                            <div class="stat-value">{total_amount:,.2f} SAR</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Unique Transactions</div>
                            <div class="stat-value">{unique_txns:,}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Unique Invoices</div>
                            <div class="stat-value">{unique_invoices:,}</div>
                        </div>
                    </div>
                </div>

                <!-- Date Breakdown -->
                <div class="section">
                    <h2 class="section-title">
                        <span class="section-icon">📅</span>
                        Transaction Breakdown by Date
                    </h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th class="number">Amount (SAR)</th>
                                <th class="number">Transactions</th>
                                <th class="number">Invoices</th>
                            </tr>
                        </thead>
                        <tbody>
    """

    # Add date rows
    for _, row in date_summary.iterrows():
        html_content += f"""
                            <tr>
                                <td>{html.escape(str(row['Date']))}</td>
                                <td class="number">{row['Total Amount']:,.2f}</td>
                                <td class="number">{row['Transactions']:,}</td>
                                <td class="number">{row['Invoices']:,}</td>
                            </tr>
        """

    # Add total row
    html_content += f"""
                        </tbody>
                        <tfoot>
                            <tr>
                                <td>TOTAL</td>
                                <td class="number">{date_summary['Total Amount'].sum():,.2f}</td>
                                <td class="number">{date_summary['Transactions'].sum():,}</td>
                                <td class="number">{date_summary['Invoices'].sum():,}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <!-- Store Breakdown -->
                <div class="section">
                    <h2 class="section-title">
                        <span class="section-icon">🏪</span>
                        Store Breakdown (Top 20)
                    </h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Store</th>
                                <th class="number">Amount (SAR)</th>
                                <th class="number">Transactions</th>
                                <th class="number">Invoices</th>
                            </tr>
                        </thead>
                        <tbody>
    """

    # Add store rows
    for _, row in store_summary.iterrows():
        html_content += f"""
                            <tr>
                                <td class="store">{html.escape(str(row['Store']))}</td>
                                <td class="number">{row['Total Amount']:,.2f}</td>
                                <td class="number">{row['Transactions']:,}</td>
                                <td class="number">{row['Invoices']:,}</td>
                            </tr>
        """

    html_content += f"""
                        </tbody>
                    </table>
                </div>

                <!-- Discount Analysis -->
                <div class="section">
                    <h2 class="section-title">
                        <span class="section-icon">💸</span>
                        Discount Items Analysis
                    </h2>
                    <div class="discount-grid">
                        <div class="discount-item">
                            <div class="label">Discount Lines</div>
                            <div class="value">{discount_count:,}</div>
                        </div>
                        <div class="discount-item">
                            <div class="label">Discount Amount</div>
                            <div class="value">{discount_amount:,.2f} SAR</div>
                        </div>
                        <div class="discount-item">
                            <div class="label">Regular Lines</div>
                            <div class="value">{regular_count:,}</div>
                        </div>
                        <div class="discount-item">
                            <div class="label">Regular Amount</div>
                            <div class="value">{regular_amount:,.2f} SAR</div>
                        </div>
                        <div class="discount-item">
                            <div class="label">Discount Percentage</div>
                            <div class="value">{discount_pct:.2f}%</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p><strong>Oracle Fusion Financial Integration</strong></p>
                <p>Professional Report Generator • Enterprise Edition</p>
                <p>For questions or support, contact your system administrator</p>
            </div>
        </div>
    </body>
    </html>
    """

    html_bytes = html_content.encode('utf-8')

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
    Generate HTML comparing AR Invoice totals with input sheet totals with visual design.

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
    import html

    match_threshold = 0.01
    difference = abs(ar_total - input_total)
    is_match = difference < match_threshold
    status_icon = "✅" if is_match else "⚠️"
    status_text = "MATCH" if is_match else "MISMATCH"
    status_class = "success" if is_match else "warning"

    escaped_filename = html.escape(Path(ar_invoice_path).name)
    timestamp = datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>AR Invoice Comparison Report</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 40px 20px;
                color: #1a202c;
                line-height: 1.6;
            }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }}

            .header {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
                padding: 48px 40px;
                text-align: center;
            }}

            .header h1 {{
                font-size: 36px;
                font-weight: 800;
                margin-bottom: 12px;
                letter-spacing: -0.5px;
            }}

            .header .subtitle {{
                font-size: 16px;
                opacity: 0.95;
                font-weight: 400;
            }}

            .header .file-info {{
                margin-top: 24px;
                padding: 16px 24px;
                background: rgba(255,255,255,0.15);
                border-radius: 8px;
                display: inline-block;
                backdrop-filter: blur(10px);
            }}

            .header .file-info strong {{
                display: block;
                font-size: 14px;
                margin-bottom: 4px;
                opacity: 0.9;
            }}

            .content {{
                padding: 40px;
            }}

            .status-banner {{
                padding: 32px;
                border-radius: 12px;
                margin-bottom: 32px;
                text-align: center;
                font-size: 24px;
                font-weight: 700;
            }}

            .status-banner.success {{
                background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
                color: #0c4128;
            }}

            .status-banner.warning {{
                background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                color: #741b47;
            }}

            .comparison-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 24px;
                margin-bottom: 40px;
            }}

            .comparison-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 28px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }}

            .comparison-card.difference {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }}

            .comparison-card .label {{
                font-size: 13px;
                opacity: 0.9;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 12px;
            }}

            .comparison-card .value {{
                font-size: 36px;
                font-weight: 800;
                letter-spacing: -1px;
                font-family: 'JetBrains Mono', monospace;
            }}

            .section-title {{
                font-size: 24px;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 24px;
                padding-bottom: 12px;
                border-bottom: 3px solid #667eea;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                border-radius: 8px;
                overflow: hidden;
            }}

            thead {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}

            thead th {{
                padding: 16px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            thead th.number {{
                text-align: right;
            }}

            tbody tr {{
                border-bottom: 1px solid #e2e8f0;
                transition: background 0.2s;
            }}

            tbody tr:hover {{
                background: #f7fafc;
            }}

            tbody tr:last-child {{
                border-bottom: none;
            }}

            tbody td {{
                padding: 14px 16px;
                font-size: 14px;
            }}

            tbody td.number {{
                text-align: right;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 600;
                color: #2d3748;
            }}

            .footer {{
                background: #f7fafc;
                padding: 32px 40px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
            }}

            .footer p {{
                color: #718096;
                font-size: 14px;
                margin: 4px 0;
            }}

            .footer strong {{
                color: #2d3748;
                font-weight: 700;
            }}

            @media print {{
                body {{
                    background: white;
                    padding: 0;
                }}

                .container {{
                    box-shadow: none;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔄 Comparison Report</h1>
                <p class="subtitle">AR Invoice vs Input Sheet Verification</p>
                <div class="file-info">
                    <strong>📁 {escaped_filename}</strong>
                    {timestamp}
                </div>
            </div>

            <div class="content">
                <!-- Status Banner -->
                <div class="status-banner {status_class}">
                    {status_icon} Verification Status: {status_text}
                </div>

                <!-- Comparison Cards -->
                <div class="comparison-cards">
                    <div class="comparison-card">
                        <div class="label">AR Invoice Total</div>
                        <div class="value">{ar_total:,.2f} SAR</div>
                    </div>
                    <div class="comparison-card">
                        <div class="label">Input Sheet Total</div>
                        <div class="value">{input_total:,.2f} SAR</div>
                    </div>
                    <div class="comparison-card difference">
                        <div class="label">Difference</div>
                        <div class="value">{difference:,.2f} SAR</div>
                    </div>
                </div>
    """

    # Add date-wise breakdown if available
    if date_breakdown:
        html_content += """
                <!-- Date-wise Breakdown -->
                <h2 class="section-title">📅 Date-wise Breakdown</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th class="number">AR Amount (SAR)</th>
                            <th class="number">Input Amount (SAR)</th>
                            <th class="number">Difference (SAR)</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for date, amounts in sorted(date_breakdown.items()):
            ar_amt = amounts.get('ar', 0)
            input_amt = amounts.get('input', 0)
            diff = abs(ar_amt - input_amt)
            html_content += f"""
                        <tr>
                            <td>{html.escape(str(date))}</td>
                            <td class="number">{ar_amt:,.2f}</td>
                            <td class="number">{input_amt:,.2f}</td>
                            <td class="number">{diff:,.2f}</td>
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>
        """

    html_content += """
            </div>

            <div class="footer">
                <p><strong>Oracle Fusion Financial Integration</strong></p>
                <p>Professional Report Generator • Enterprise Edition</p>
                <p>For questions or support, contact your system administrator</p>
            </div>
        </div>
    </body>
    </html>
    """

    html_bytes = html_content.encode('utf-8')

    # Save if output path provided
    if output_path:
        Path(output_path).write_bytes(html_bytes)

    return html_bytes
