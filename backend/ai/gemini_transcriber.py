import os
import json
import asyncio
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class TranscriptSegment(BaseModel):
    speaker: str = Field(description="The identifier for the speaker, e.g., 'Speaker A', 'Speaker B'.")
    text: str = Field(description="The exact transcribed text spoken by this speaker.")
    start: float = Field(description="Approximate start time in seconds relative to the chunk (use 0.0 if unknown).")
    end: float = Field(description="Approximate end time in seconds relative to the chunk (use 0.0 if unknown).")

class DiarizedTranscript(BaseModel):
    segments: list[TranscriptSegment]

class GeminiTranscriber:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        
    def _transcribe_sync(self, file_path: str, chunk_offset: float = 0.0):
        print(f"Uploading {file_path} to Gemini...")
        uploaded_file = self.client.files.upload(file=file_path)
        
        prompt = """
        You are a precise transcription system. 
        Your task is to transcribe EVERY SINGLE WORD of the provided audio from the very beginning to the very end.
        Transcribe the audio in its ORIGINAL spoken language (e.g., if the speaker speaks Chinese, output Chinese characters).
        DO NOT summarize, DO NOT skip any parts, and DO NOT truncate the output.
        Please transcribe the audio and diarize the speakers.
        Identify different speakers as Speaker A, Speaker B, etc.
        
        CRITICAL FORMATTING INSTRUCTION: 
        You MUST break down the transcription into very short segments (e.g. 1 to 10 seconds each, or single sentences/phrases). 
        Do NOT group a speaker's long monologue into a single large segment. 
        Instead, create a new JSON array object for every new sentence or short breath a speaker takes.

        Output the precise transcript as a JSON array where each object contains the speaker name, the transcribed text, and approximate start/end timestamps in seconds relative to the start of this audio clip.
        """
        
        print(f"Calling Gemini 3.5 Flash Lite for transcription and diarization...")
        response = self.client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DiarizedTranscript,
                temperature=0.2,
            ),
        )
        
        # Cleanup file from Gemini servers
        try:
            self.client.files.delete(name=uploaded_file.name)
        except Exception as e:
            print(f"Failed to delete Gemini file {uploaded_file.name}: {e}")
        
        total_tokens = 0
        if response.usage_metadata:
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0)
            
        segments = []
        if response.parsed:
            for seg in response.parsed.segments:
                segments.append({
                    "speaker": seg.speaker,
                    "text": seg.text,
                    "start": seg.start + chunk_offset,
                    "end": seg.end + chunk_offset
                })
        else:
            # Fallback if parsed is not directly populated but text is JSON
            try:
                data = json.loads(response.text)
                for seg in data.get("segments", []):
                    segments.append({
                        "speaker": seg.get("speaker", "Unknown"),
                        "text": seg.get("text", ""),
                        "start": seg.get("start", 0.0) + chunk_offset,
                        "end": seg.get("end", 0.0) + chunk_offset
                    })
            except Exception as e:
                print(f"Error parsing fallback JSON: {e}")
                
        return segments, total_tokens

    async def transcribe_and_diarize(self, file_path: str, chunk_offset: float = 0.0):
        return await asyncio.to_thread(self._transcribe_sync, file_path, chunk_offset)
