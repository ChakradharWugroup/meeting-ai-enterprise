import io
import time
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.colors import HexColor
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

try:
    pdfmetrics.registerFont(TTFont('MSYH', r'C:\Windows\Fonts\msyh.ttc'))
    pdfmetrics.registerFont(TTFont('MSYH-Bold', r'C:\Windows\Fonts\msyhbd.ttc'))
    DEFAULT_FONT = 'MSYH'
    DEFAULT_FONT_BOLD = 'MSYH-Bold'
except Exception as e:
    print(f"Warning: Could not load Chinese fonts: {e}")
    DEFAULT_FONT = 'Helvetica'
    DEFAULT_FONT_BOLD = 'Helvetica-Bold'

def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(DEFAULT_FONT, 9)
    canvas.setFillColor(HexColor('#6b7280')) # Gray-500
    # Light gray line
    canvas.setStrokeColor(HexColor('#e5e7eb'))
    canvas.line(doc.leftMargin, 50, doc.width + doc.leftMargin, 50)
    
    # Left side
    canvas.drawString(doc.leftMargin, 35, "Confidential - Meeting AI Report")
    
    # Right side
    page_num = f"Page {doc.page} of {doc.page}" # Simple 'Page X', can't easily do 'of Y' in simpledoc without two passes, but 'Page X' is fine
    canvas.drawRightString(doc.width + doc.leftMargin, 35, f"Page {doc.page}")
    canvas.restoreState()

def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def generate_transcript_pdf(meeting_title: str, transcript: str, segments: list = None) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=24,
        textColor=HexColor('#1e3a8a'), # Dark blue matching screenshot
        spaceAfter=30
    )
    
    speaker_style = ParagraphStyle(
        'SpeakerName',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT_BOLD,
        fontSize=12,
        textColor=HexColor('#2563eb'), # Bright blue matching screenshot
        spaceAfter=6,
        spaceBefore=16
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName=DEFAULT_FONT,
        fontSize=11,
        textColor=HexColor('#374151'),
        leading=16,
        spaceAfter=12
    )
    
    meta_key_style = ParagraphStyle('MetaKey', parent=styles['Normal'], fontName=DEFAULT_FONT_BOLD, fontSize=10, textColor=HexColor('#4b5563'))
    meta_val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontName=DEFAULT_FONT, fontSize=10, textColor=HexColor('#1f2937'))
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"Transcript: {meeting_title}", title_style))
    
    # Metadata Table
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration_str = "Unknown"
    if segments and len(segments) > 0:
        last = segments[-1]
        if 'end_str' in last:
            duration_str = last['end_str']
        elif 'end' in last:
            duration_str = format_time(last['end'])
        
    meta_data = [
        [Paragraph("Date:", meta_key_style), Paragraph(date_str, meta_val_style)],
        [Paragraph("Duration:", meta_key_style), Paragraph(duration_str, meta_val_style)],
        [Paragraph("Total Segments:", meta_key_style), Paragraph(str(len(segments)) if segments else "0", meta_val_style)]
    ]
    
    # Create table with no borders except bottom
    meta_table = Table(meta_data, colWidths=[120, 300])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, HexColor('#e5e7eb')),
    ]))
    
    elements.append(meta_table)
    elements.append(Spacer(1, 20))
    
    # Transcript segments
    if segments:
        for seg in segments:
            speaker = escape(seg.get('speaker', 'Speaker'))
            # Support both float seconds (old Gemini format) and HH:MM:SS strings (subtitle format)
            if 'start_str' in seg:
                start_fmt = escape(seg['start_str'])
                end_fmt = escape(seg['end_str'])
            else:
                start_fmt = escape(format_time(seg.get('start', 0.0)))
                end_fmt = escape(format_time(seg.get('end', 0.0)))
            text = escape(seg.get('text', ''))
            
            # Speaker line
            elements.append(Paragraph(f"{speaker} ({start_fmt} - {end_fmt})", speaker_style))
            # Text line
            elements.append(Paragraph(text, body_style))
    else:
        # Fallback to plain transcript if no segments
        if not transcript:
            transcript = "No transcript generated."
        for line in transcript.split('\n'):
            elements.append(Paragraph(escape(line), body_style))
        
    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer

def generate_summary_pdf(meeting_title: str, summary: str) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=72, leftMargin=72,
        topMargin=72, bottomMargin=72
    )
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'SummaryTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=HexColor('#1e3a8a'),
        spaceAfter=30
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=HexColor('#374151'),
        leading=16,
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=HexColor('#2563eb'),
        spaceAfter=10,
        spaceBefore=20
    )

    h3_style = ParagraphStyle(
        'H3',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=HexColor('#4b5563'),
        spaceAfter=8,
        spaceBefore=16
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=HexColor('#374151'),
        leading=16,
        leftIndent=20,
        spaceAfter=8
    )
    
    elements = []
    elements.append(Paragraph(f"AI Speaker Analysis: {meeting_title}", title_style))
    
    # Parse Markdown from Ollama to rudimentary PDF elements
    if not summary:
        summary = "No summary generated."
        
    for line in summary.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Rudimentary markdown parsing for H2, H3, and bullets
        if line.startswith('## '):
            elements.append(Paragraph(escape(line[3:]), h2_style))
        elif line.startswith('### '):
            elements.append(Paragraph(escape(line[4:]), h3_style))
        elif line.startswith('- ') or line.startswith('* '):
            elements.append(Paragraph(f"• {escape(line[2:])}", bullet_style))
        else:
            # Check for bold tags (**text**) - we can replace them with <b>text</b> for reportlab
            import re
            line = escape(line)
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            elements.append(Paragraph(line, body_style))
            
    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    buffer.seek(0)
    return buffer
