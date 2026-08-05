import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

class EmailDispatcher:
    def __init__(self):
        # In a real environment, these come from .env
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER", "your-bot-email@gmail.com")
        self.smtp_pass = os.getenv("SMTP_PASS", "your-app-password")

    def send_meeting_report(self, recipient_email: str, meeting_title: str, report_filepath: str):
        """
        Sends the generated PDF/DOCX report to the employee.
        """
        print(f"Preparing to email report to {recipient_email}...")
        
        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = f"[Meeting AI] Your Transcript & Action Items: {meeting_title}"

        # Body
        body = f"Hello,\n\nAttached is the AI-generated report for your recent meeting: '{meeting_title}'.\n\nBest,\nYour Enterprise AI Assistant"
        msg.attach(MIMEText(body, 'plain'))

        # Attachment
        if os.path.exists(report_filepath):
            with open(report_filepath, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(report_filepath))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_filepath)}"'
            msg.attach(part)
        else:
            print("Error: Report file not found for attachment.")
            return False

        # Attempt to send (Will fail locally without real credentials)
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            # server.login(self.smtp_user, self.smtp_pass)
            # server.send_message(msg)
            server.quit()
            print(f"Mock Success: Email would have been sent to {recipient_email} via {self.smtp_server}.")
            return True
        except Exception as e:
            print(f"SMTP Error: Ensure you have real credentials in your .env file. Details: {e}")
            return False
