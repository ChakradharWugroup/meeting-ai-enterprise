import os
from ollama import AsyncClient

# Use localhost mapping for local testing, or docker internal hostname in production
host_url = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11435')
client = AsyncClient(host=host_url)

class MeetingSummarizer:
    def __init__(self, model_name: str = "qwen2:0.5b"):
        self.model_name = model_name

    async def generate_incremental_summary(self, new_transcript: str, current_summary: str) -> str:
        """
        Takes the existing summary and updates it with the latest transcript snippet.
        """
        prompt = f"""
        You are an AI meeting assistant. Update the current meeting summary with the new transcript.
        
        Current Summary:
        {current_summary}
        
        New Transcript:
        {new_transcript}
        
        Provide an updated, concise summary.
        """
        print(f"Calling Ollama ({self.model_name}) for incremental summary...")
        try:
            response = await client.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content']
        except Exception as e:
            print(f"Ollama error: {e}")
            return current_summary

    async def generate_final_summary(self, full_transcript: str) -> str:
        """
        Generates a comprehensive executive summary at the end of the meeting.
        """
        print(f"Generating final meeting summary via Ollama ({self.model_name})...")
        prompt = f"Provide a comprehensive executive summary of the following meeting transcript:\n\n{full_transcript}"
        try:
            response = await client.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}])
            return response['message']['content']
        except Exception as e:
            print(f"Ollama error: {e}")
            return "Failed to generate final summary."
