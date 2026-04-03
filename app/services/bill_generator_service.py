import os
from datetime import datetime
from typing import Optional, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_pdf_bill(order_data: dict, shop_info: Optional[Dict[str, Any]] = None,
                      customer_data: Optional[dict] = None, storage_path: str = "/tmp/bills") -> str:
    """
    Generate a PDF bill for an order.
    
    Args:
        order_data: Order details from database
        shop_info: Optional dict with shop details (business_name, address, phone, gst_number, terms)
        customer_data: Customer details (optional)
        storage_path: Directory to store PDF files
        
    Returns:
        Path to generated PDF file
    """
    # Ensure storage directory exists
    os.makedirs(storage_path, exist_ok=True)
    
    # Generate filename
    order_id = str(order_data.get("id", order_data.get("_id", "unknown")))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bill_{order_id}_{timestamp}.pdf"
    filepath = os.path.join(storage_path, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Container for elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Header Style
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#4B0082'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    # Shop Name Style
    shop_style = ParagraphStyle(
        'ShopStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    # Normal text style
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    # Right aligned style
    right_style = ParagraphStyle(
        'RightStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT
    )
    
    # Shop Header
    shop_name = shop_info.get("business_name", "My Shop") if shop_info else "My Shop"
    elements.append(Paragraph(shop_name, shop_style))
    
    # Greeting Message (if provided)
    if shop_info and shop_info.get("greeting_message"):
        greeting_style = ParagraphStyle(
            'GreetingStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=6
        )
        elements.append(Paragraph(shop_info["greeting_message"], greeting_style))
    
    # Shop Address
    if shop_info:
        address_parts = []
        if shop_info.get("address"):
            address_parts.append(shop_info["address"])
        if shop_info.get("city"):
            address_parts.append(shop_info["city"])
        if shop_info.get("state"):
            address_parts.append(shop_info["state"])
        if shop_info.get("postal_code"):
            address_parts.append(shop_info["postal_code"])
        
        if address_parts:
            address_text = ", ".join(address_parts)
            elements.append(Paragraph(address_text, normal_style))
        
        if shop_info.get("phone"):
            elements.append(Paragraph(f"Phone: {shop_info['phone']}", normal_style))
        if shop_info.get("email"):
            elements.append(Paragraph(f"Email: {shop_info['email']}", normal_style))
        if shop_info.get("gst_number"):
            elements.append(Paragraph(f"GST: {shop_info['gst_number']}", normal_style))
    
    elements.append(Spacer(1, 12))
    
    # Bill Title
    elements.append(Paragraph("TAX INVOICE", header_style))
    elements.append(Spacer(1, 12))
    
    # Bill Info Table
    bill_date = order_data.get("created_at", datetime.now())
    if isinstance(bill_date, str):
        try:
            bill_date = datetime.fromisoformat(bill_date.replace('Z', '+00:00'))
        except:
            bill_date = datetime.now()
    
    formatted_date = bill_date.strftime("%d-%m-%Y %H:%M")
    
    bill_info = [
        ["Bill No:", order_id[-8:].upper()],
        ["Date:", formatted_date],
    ]
    
    if customer_data:
        bill_info.append(["Customer:", customer_data.get("name", "Walk-in Customer")])
        if customer_data.get("phone"):
            bill_info.append(["Phone:", customer_data.get("phone")])
    else:
        bill_info.append(["Customer:", "Walk-in Customer"])
    
    bill_info.append(["Payment:", order_data.get("payment_method", "Cash").upper()])
    
    bill_table = Table(bill_info, colWidths=[3*cm, 10*cm])
    bill_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(bill_table)
    elements.append(Spacer(1, 12))
    
    # Items Table Header
    items_data = [["#", "Item", "Qty", "Price", "Amount"]]
    
    # Items
    items = order_data.get("items", [])
    subtotal = 0
    
    for idx, item in enumerate(items, 1):
        name = item.get("name", "Unknown")
        qty = item.get("quantity", 0)
        price = item.get("price", 0)
        amount = qty * price
        subtotal += amount
        
        items_data.append([
            str(idx),
            name,
            str(qty),
            f"₹{price:.2f}",
            f"₹{amount:.2f}"
        ])
    
    # Items Table
    items_table = Table(items_data, colWidths=[1*cm, 8*cm, 2*cm, 3*cm, 3*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4B0082')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F0F0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 12))
    
    # Totals
    discount = order_data.get("discount", 0) or 0
    discount_amount = subtotal * (discount / 100) if discount > 0 else 0
    total = subtotal - discount_amount
    
    totals_data = []
    
    if discount > 0:
        totals_data.append(["Subtotal:", f"₹{subtotal:.2f}"])
        totals_data.append([f"Discount ({discount}%):", f"-₹{discount_amount:.2f}"])
        totals_data.append(["Total:", f"₹{total:.2f}"])
    else:
        totals_data.append(["Total:", f"₹{subtotal:.2f}"])
    
    totals_table = Table(totals_data, colWidths=[10*cm, 7*cm])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#4B0082')),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TOPPADDING', (0, -1), (-1, -1), 8),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(totals_table)
    elements.append(Spacer(1, 20))
    
    # Terms and Footer
    footer_message = shop_info.get("terms_conditions", "Thank you for your business!") if shop_info else "Thank you for your business!"
    if footer_message:
        elements.append(Paragraph(footer_message, normal_style))
    
    elements.append(Spacer(1, 12))
    
    # Generated timestamp
    footer_text = f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | Powered by RetailFlow"
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    
    return filepath


def format_currency(amount: float) -> str:
    """Format amount as Indian Rupees."""
    return f"₹{amount:.2f}"
