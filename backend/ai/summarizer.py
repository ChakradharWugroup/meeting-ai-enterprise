import aiohttp
import json

class MeetingSummarizer:
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    async def generate_incremental_summary(self, new_transcript: str, current_summary: str) -> str:
        """
        Takes the existing summary and updates it with the latest transcript snippet using local Ollama.
        """
        prompt = f"""
        You are an AI meeting assistant. Update the current meeting summary with the new transcript.
        Current Summary:
        {current_summary}
        
        New Transcript:
        {new_transcript}
        
        Provide an updated, concise summary.
        """
        return await self._call_ollama(prompt) or current_summary

    async def generate_final_summary(self, full_transcript: str) -> str:
        """
        Generates a comprehensive executive summary at the end of the meeting using local Ollama.
        """
        prompt = f"Provide a comprehensive executive summary of the following meeting transcript:\n\n{full_transcript}"
        return await self._call_ollama(prompt) or "Failed to generate final summary."

    async def _call_ollama(self, prompt: str) -> str:
        print(f"Calling local Ollama ({self.model_name}) for summary...")
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
                async with session.post(self.api_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        error_text = await response.text()
                        print(f"Ollama error {response.status}: {error_text}")
                        return ""
        except Exception as e:
            print(f"Ollama connection error: {e}. Is the Ollama daemon running?")
            return ""
