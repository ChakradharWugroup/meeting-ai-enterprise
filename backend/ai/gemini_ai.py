import os
from google import genai
from google.genai import types
import json

class GeminiTranscriber:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    async def transcribe_and_diarize(self, file_path: str, mime_type: str = "audio/mp3"):
        """
        Uploads audio to Gemini, transcribes it, and diarizes speakers using gemini-2.5-flash.
        """
        if not self.client:
            raise Exception("Gemini API key is not set.")

        print(f"Uploading file to Gemini: {file_path}")
        gemini_file = self.client.files.upload(file=file_path, config={"mime_type": mime_type})
        
        # Wait for the file to be ACTIVE on Google's servers before generating content
        import time
        while True:
            file_info = self.client.files.get(name=gemini_file.name)
            if file_info.state.name == "ACTIVE":
                print("File is ACTIVE and ready for transcription.")
                break
            elif file_info.state.name == "FAILED":
                raise Exception("Gemini file processing failed on Google's servers.")
            print(f"Waiting for Gemini to process audio file (Current state: {file_info.state.name})...")
            time.sleep(3)
        
        prompt = """
Please listen to this audio file and provide a complete transcript. 
You must separate the speech by speaker and provide timestamps for when each speaker speaks.

CRITICAL INSTRUCTION:
Do NOT group a speaker's continuous speech into one long segment! 
You MUST break the speech down into very short, bite-sized segments. Each segment should contain only one short sentence or phrase, and its duration (end - start) MUST NOT exceed 5 seconds. 

For example, if someone speaks continuously for 40 seconds, you must output 10 to 15 separate segments for that speaker, each spanning just 2 to 5 seconds.

Return the result ONLY as a JSON object in this exact format:
{
  "text": "The full combined transcript text here.",
  "segments": [
    {
      "speaker": "Speaker 1",
      "start": 0.0,
      "end": 3.5,
      "text": "First short phrase."
    },
    {
      "speaker": "Speaker 1",
      "start": 3.5,
      "end": 7.0,
      "text": "Second short phrase."
    }
  ]
}
"""
        import json
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    print(f"Generating transcript with Gemini 3.5 Flash Lite...")
                else:
                    print(f"Retry {attempt}/{max_retries} for Gemini 3.5 Flash Lite...")
                    
                response = self.client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=[gemini_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        max_output_tokens=8192
                    )
                )
                
                # Sanitize the output in case Gemini wrapped it in markdown blocks
                raw_text = response.text.strip()
                print(f"Gemini Raw Output: {raw_text[:200]}...")
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                
                result = json.loads(raw_text)
                
                formatted_segments = []
                for seg in result.get("segments", []):
                    formatted_segments.append({
                        "speaker": seg.get("speaker", "Speaker"),
                        "start": float(seg.get("start", 0.0)),
                        "end": float(seg.get("end", 0.0)),
                        "text": seg.get("text", "").strip()
                    })
                    
                # Clean up the file from Google's servers
                try:
                    self.client.files.delete(name=gemini_file.name)
                except Exception as e:
                    print(f"Warning: Failed to delete Gemini file {gemini_file.name}: {e}")
                    
                return {
                    "text": result.get("text", ""),
                    "segments": formatted_segments
                }
                
            except json.JSONDecodeError as je:
                print(f"JSON Parse Error on attempt {attempt+1}: {je}")
                if attempt == max_retries - 1:
                    print(f"Raw output that failed: {response.text}")
                    try:
                        self.client.files.delete(name=gemini_file.name)
                    except:
                        pass
                    raise Exception(f"Failed to parse Gemini JSON after {max_retries} attempts.")
            except Exception as e:
                print(f"Gemini API Error on attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    try:
                        self.client.files.delete(name=gemini_file.name)
                    except:
                        pass
                    raise e

