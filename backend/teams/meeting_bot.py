import logging

class TeamsMeetingBot:
    def __init__(self):
        self.active_meetings = {}

    async def join_meeting(self, meeting_url: str) -> str:
        """
        Joins a Microsoft Teams meeting via Graph API/Cloud Communications API.
        Returns a meeting_id.
        """
        logging.info(f"Bot attempting to join meeting: {meeting_url}")
        
        # Mock API interaction
        meeting_id = "teams_meeting_" + str(hash(meeting_url) % 1000)
        self.active_meetings[meeting_id] = {"status": "joined", "url": meeting_url}
        return meeting_id

    async def leave_meeting(self, meeting_id: str):
        """
        Leaves the meeting.
        """
        logging.info(f"Bot leaving meeting: {meeting_id}")
        if meeting_id in self.active_meetings:
            self.active_meetings[meeting_id]["status"] = "left"
