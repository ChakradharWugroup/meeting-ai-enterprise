import os
from groq import AsyncGroq

class MeetingSummarizer:
    def __init__(self, model_name: str = "llama3-8b-8192"):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            self.client = None
        self.model_name = model_name

    async def generate_incremental_summary(self, new_transcript: str, current_summary: str) -> str:
        """
        Takes the existing summary and updates it with the latest transcript snippet.
        """
        if not self.client:
            return current_summary + "\n" + new_transcript
            
        prompt = f"""
        You are an AI meeting assistant. Update the current meeting summary with the new transcript.
        Current Summary:
        {current_summary}
        
        New Transcript:
        {new_transcript}
        
        Provide an updated, concise summary.
        """
        print(f"Calling Groq ({self.model_name}) for incremental summary...")
        try:
            response = await self.client.chat.completions.create(
                messages=[{'role': 'user', 'content': prompt}],
                model=self.model_name
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq error: {e}")
            return current_summary

    async def generate_final_summary(self, full_transcript: str) -> str:
        """
        Generates a comprehensive executive summary at the end of the meeting.
        """
        if not self.client:
            return "No API key configured for final summary."
            
        print(f"Generating final meeting summary via Groq ({self.model_name})...")
        prompt = f"Provide a comprehensive executive summary of the following meeting transcript:\n\n{full_transcript}"
        try:
            response = await self.client.chat.completions.create(
                messages=[{'role': 'user', 'content': prompt}],
                model=self.model_name
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Groq error: {e}")
            return "Failed to generate final summary."
