import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.colors import HexColor

class PDFReportGenerator:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate_report(self, meeting_title: str, summary: str, action_items: list, transcript: str) -> str:
        """
        Generates a beautifully styled PDF report and returns the file path.
        """
        safe_title = "".join([c for c in meeting_title if c.isalpha() or c.isdigit()]).rstrip()
        filename = f"{self.output_dir}/{safe_title}_Report.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#4c1d95'), # Deep purple branding
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#333333'),
            spaceBefore=20,
            spaceAfter=10
        )
        
        story = []
        
        # Title
        story.append(Paragraph(f"Enterprise AI Meeting Report: {meeting_title}", title_style))
        story.append(Spacer(1, 12))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(summary, styles["Normal"]))
        story.append(Spacer(1, 12))
        
        # Action Items
        if action_items:
            story.append(Paragraph("Action Items", heading_style))
            for item in action_items:
                desc = item.get("description", "")
                owner = item.get("owner", "Unassigned")
                story.append(Paragraph(f"• <b>{owner}:</b> {desc}", styles["Normal"]))
            story.append(Spacer(1, 12))
            
        # Full Transcript
        story.append(Paragraph("Full Diarized Transcript", heading_style))
        story.append(Paragraph(transcript.replace('\n', '<br/>'), styles["Normal"]))
        
        # Build PDF
        doc.build(story)
        print(f"Generated PDF: {filename}")
        return filename
