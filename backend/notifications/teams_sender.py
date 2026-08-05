class TeamsNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_meeting_summary(self, meeting_id: str, summary: str, document_urls: list[str]):
        """
        Posts the final AI consolidation into the Teams Meeting Chat.
        """
        print(f"Posting summary to Teams chat for meeting {meeting_id}...")
        # In real life, use Adaptive Cards sent to a Webhook URL or via Graph API
        return True
