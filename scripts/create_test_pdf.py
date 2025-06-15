#!/usr/bin/env python3
"""
Script to create a test PDF invoice
"""
import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_test_invoice(output_path):
    """Create a test invoice PDF"""
    # Create output directory if it doesn't exist
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6
    ))
    
    # Content
    elements = []
    
    # Title
    elements.append(Paragraph("INVOICE #INV-2023-001", styles['InvoiceTitle']))
    
    # Invoice info
    elements.append(Paragraph("Date: 2023-11-15"))
    elements.append(Paragraph("Due Date: 2023-12-15"))
    elements.append(Spacer(1, 20))
    
    # From/To sections
    from_text = """
    <b>From:</b><br/>
    Your Company Inc.<br/>
    123 Business Rd.<br/>
    New York, NY 10001<br/>
    Email: billing@yourcompany.com<br/>
    Tax ID: US123456789
    """
    
    to_text = """
    <b>To:</b><br/>
    Acme Corp<br/>
    456 Customer St<br/>
    Boston, MA 02108<br/>
    Email: accounts@acmecorp.com<br/>
    Tax ID: US987654321
    """
    
    from_para = Paragraph(from_text, styles['Normal'])
    to_para = Paragraph(to_text, styles['Normal'])
    
    # Create a 2-column table for From/To
    from_to_data = [[from_para, to_para]]
    from_to_table = Table(from_to_data, colWidths=[doc.width/2.0]*2)
    from_to_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(from_to_table)
    elements.append(Spacer(1, 20))
    
    # Items table
    elements.append(Paragraph("Invoice Items", styles['SectionHeader']))
    
    # Table data
    data = [
        ['Description', 'Qty', 'Unit Price', 'Total'],
        ['Web Design Services', '10', '$100.00', '$1,000.00'],
        ['Hosting (Monthly)', '1', '$50.00', '$50.00'],
        ['Domain Registration', '1', '$15.00', '$15.00'],
    ]
    
    # Create table
    table = Table(data, colWidths=[doc.width*0.5, doc.width*0.1, doc.width*0.2, doc.width*0.2])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),  # Qty
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Prices
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Totals
    elements.append(Paragraph("Subtotal: $1,065.00", styles['Normal']))
    elements.append(Paragraph("Tax (8%): $85.20", styles['Normal']))
    elements.append(Paragraph("<b>Total: $1,150.20</b>", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Payment terms and notes
    elements.append(Paragraph("<b>Payment Terms:</b> Net 30", styles['Normal']))
    elements.append(Paragraph("Please make checks payable to Your Company Inc.", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>Notes:</b>", styles['Normal']))
    elements.append(Paragraph("Thank you for your business!", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>Additional Information:</b>", styles['Normal']))
    elements.append(Paragraph("- This is a sample invoice for testing purposes", styles['Normal']))
    elements.append(Paragraph("- Please contact us with any questions", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    print(f"Created test invoice: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        output_path = "tests/data/sample_invoice.pdf"
    
    create_test_invoice(output_path)
