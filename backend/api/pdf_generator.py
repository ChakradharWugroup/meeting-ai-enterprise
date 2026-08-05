import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.colors import HexColor

def generate_meeting_pdf(meeting_title: str, summary: str, transcript: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor('#4c1d95'), # Purple-900
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=HexColor('#3b82f6'), # Blue-500
        spaceAfter=12,
        spaceBefore=20
    )
    
    body_style = styles['Normal']
    body_style.fontSize = 11
    body_style.leading = 14
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"AI Intelligence Report: {meeting_title}", title_style))
    
    # Summary
    elements.append(Paragraph("Executive Summary", heading_style))
    elements.append(Paragraph(summary, body_style))
    elements.append(Spacer(1, 20))
    
    # Transcript
    elements.append(Paragraph("Full Transcript", heading_style))
    
    # Mock some transcript lines if not provided
    if not transcript:
        transcript = "[00:00] Bot: AI Notetaker joined the meeting.\n[00:15] Speaker 1: Okay let's get started.\n[00:45] Speaker 2: Agreed, here is the new architecture plan."
        
    for line in transcript.split('\n'):
        elements.append(Paragraph(line, body_style))
        elements.append(Spacer(1, 6))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer
