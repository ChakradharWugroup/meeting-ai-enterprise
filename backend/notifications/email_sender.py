class EmailNotifier:
    def __init__(self, smtp_server: str):
        self.smtp_server = smtp_server

    async def send_email(self, to_emails: list[str], subject: str, body: str, attachments: list[str] = None):
        """
        Sends an email with the meeting minutes.
        """
        print(f"Sending email to {len(to_emails)} participants: {subject}")
        return True
