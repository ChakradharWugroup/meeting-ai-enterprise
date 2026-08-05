import json
import os
from ollama import AsyncClient

host_url = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11435')
client = AsyncClient(host=host_url)

class ActionItemExtractor:
    def __init__(self, model_name: str = "qwen2:0.5b"):
        self.model_name = model_name

    async def extract_action_items(self, transcript_chunk: str) -> list[dict]:
        """
        Extracts tasks, owners, and deadlines from the transcript.
        Returns a list of dictionaries: {"description": "...", "owner": "..."}
        """
        print(f"Extracting action items via Ollama ({self.model_name})...")
        prompt = f"""
        Extract any action items or tasks from this meeting transcript chunk. 
        Output ONLY a valid JSON array of objects with keys "description" and "owner".
        If there are none, output [].
        Transcript: {transcript_chunk}
        """
        
        try:
            response = await client.chat(model=self.model_name, messages=[{'role': 'user', 'content': prompt}])
            content = response['message']['content']
            # Very basic JSON parsing from LLM output, assuming it follows instructions
            # In production, use structured output parsing or regex extraction
            if "[" in content and "]" in content:
                json_str = content[content.find("["):content.rfind("]")+1]
                return json.loads(json_str)
            return []
        except Exception as e:
            print(f"Ollama error extracting action items: {e}")
            return []
