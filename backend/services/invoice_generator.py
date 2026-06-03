import os
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

def generate_trip_invoice(trip_data):
    """DB data se ek clean PDF invoice banata hai"""
    pnr = trip_data.get("pnr", "UNKNOWN")
    passenger = trip_data.get("passenger_name", "Passenger")
    expenses = trip_data.get("expenses", [])
    total_amount = trip_data.get("total_amount", 0)
    
    # File name aur path set karna
    file_name = f"Agentra_Invoice_{pnr}.pdf"
    file_path = os.path.join(os.getcwd(), file_name)
    
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, spaceAfter=15, textColor=colors.HexColor("#1e3a8a"))
    story.append(Paragraph(f"AGENTRA AI - TRIP INVOICE", title_style))
    story.append(Paragraph(f"<b>Passenger:</b> {passenger} | <b>PNR:</b> {pnr}", styles["Normal"]))
    story.append(Spacer(1, 20))
    
    # Table Header
    table_data = [["Expense Type", "Description", "Cost (INR)", "Status"]]
    
    # Fill Table with DB Array Data
    for exp in expenses:
        table_data.append([
            exp.get("expense_type", "N/A"),
            exp.get("description", "N/A"),
            f"₹{exp.get('cost', 0)}",
            exp.get("status", "COMPLETED")
        ])
        
    # Add Total Row
    table_data.append(["", "", "GRAND TOTAL:", f"₹{total_amount}"])
    
    # Style the table
    table = Table(table_data, colWidths=[100, 220, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -2), 1, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'), # Total row bold
        ('TEXTCOLOR', (2, -1), (-1, -1), colors.HexColor("#b91c1c"))
    ]))
    
    story.append(table)
    story.append(Spacer(1, 30))
    story.append(Paragraph("Thank you for traveling autonomously with Agentra!", styles["Italic"]))
    
    doc.build(story)
    return file_path

def send_invoice_via_telegram(chat_id, file_path, total_amount):
    """Generate hui PDF ko Telegram par bhejta hai"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    caption = (
        f"🎉 <b>Welcome to your destination!</b>\n\n"
        f"Your end-to-end trip handled by Agentra is now complete.\n"
        f"💰 <b>Total Expenditure:</b> ₹{total_amount}\n\n"
        f"Attached is your detailed digital invoice covering Train, Cabs, Food, and Hotel. Safe stay!"
    )
    
    with open(file_path, 'rb') as doc:
        files = {'document': doc}
        data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, files=files)
        
    # Behad zaroori: file bhejne ke baad server se delete kar do taaki storage full na ho
    if os.path.exists(file_path):
        os.remove(file_path)
        
    return response.json()