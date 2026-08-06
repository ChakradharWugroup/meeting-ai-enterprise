import os
import aiohttp

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

class DeepgramAI:
    def __init__(self):
        self.api_key = DEEPGRAM_API_KEY
        if not self.api_key:
            print("WARNING: DEEPGRAM_API_KEY is not set. Deepgram transcription will fail.")

    async def transcribe_and_diarize(self, file_path: str) -> dict:
        """
        Sends an audio file to Deepgram to get transcription with speaker diarization.
        Returns a formatted dict with 'text' and 'segments'.
        """
        if not self.api_key:
            raise Exception("DEEPGRAM_API_KEY is missing. Please add it to your environment variables.")
            
        url = "https://api.deepgram.com/v1/listen?diarize=true&model=nova-2&smart_format=true"
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/mp3"
        }
        
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                async with session.post(url, headers=headers, data=f) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Deepgram API Error {response.status}: {error_text}")
                        
                    data = await response.json()
                    
        # Parse Deepgram response into our standard format
        segments_output = []
        try:
            words = data["results"]["channels"][0]["alternatives"][0]["words"]
            
            current_speaker = None
            current_segment = None
            
            for word_obj in words:
                # Deepgram returns speaker indices starting at 0
                speaker_idx = word_obj.get('speaker', 0)
                # Map 0 -> A, 1 -> B, etc.
                speaker_letter = chr(65 + speaker_idx) if speaker_idx < 26 else str(speaker_idx)
                speaker = f"Speaker {speaker_letter}"
                
                word_text = word_obj.get("punctuated_word", word_obj.get("word", ""))
                
                if current_speaker != speaker:
                    if current_segment:
                        segments_output.append(current_segment)
                    current_speaker = speaker
                    current_segment = {
                        "speaker": speaker,
                        "start": word_obj.get("start"),
                        "end": word_obj.get("end"),
                        "text": word_text
                    }
                else:
                    current_segment["end"] = word_obj.get("end")
                    current_segment["text"] += " " + word_text
                    
            if current_segment:
                segments_output.append(current_segment)
                
        except Exception as e:
            print(f"Error parsing Deepgram response: {e}")
            raise Exception("Failed to parse Deepgram speaker diarization.")
            
        return {
            "text": " ".join([s["text"] for s in segments_output]),
            "segments": segments_output
        }
