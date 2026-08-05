import time
import subprocess
import os
import threading

class CalendarScheduler:
    def __init__(self):
        self.running = False
        self.mock_meetings = [
            {"id": "mtg-001", "url": "https://teams.microsoft.com/l/meetup-join/mock", "time": time.time() + 60, "owner_email": "ceo@company.com"}
        ]

    def _poll_calendars(self):
        """
        Background thread that checks employee calendars for upcoming meetings.
        """
        while self.running:
            print("Checking calendars for upcoming meetings...")
            current_time = time.time()
            
            for mtg in list(self.mock_meetings):
                # If meeting is starting within the next minute
                if current_time >= mtg["time"] - 60:
                    print(f"Meeting {mtg['id']} is starting soon! Dispatching headless bot...")
                    self._dispatch_bot(mtg["url"], mtg["id"])
                    self.mock_meetings.remove(mtg)
                    
            time.sleep(30) # Poll every 30 seconds

    def _dispatch_bot(self, url: str, meeting_id: str):
        """
        Spawns the Playwright Node.js script in the background.
        """
        bot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "teams-bot")
        try:
            # Using subprocess to launch the Node.js headless browser bot
            subprocess.Popen(
                ["node", "join_meeting.js", url, meeting_id],
                cwd=bot_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"Successfully launched headless bot for {meeting_id}")
        except Exception as e:
            print(f"Failed to launch headless bot: {e}")

    def start(self):
        """
        Starts the background calendar polling thread.
        """
        if not self.running:
            self.running = True
            thread = threading.Thread(target=self._poll_calendars, daemon=True)
            thread.start()
            print("Calendar Auto-Scheduler activated.")

    def stop(self):
        self.running = False
