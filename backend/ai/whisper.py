import os
import io
import tempfile
from groq import Groq

class WhisperTranscriber:
    def __init__(self, model_size: str = "whisper-large-v3"):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
            print("WARNING: GROQ_API_KEY is not set. Transcription will be mocked.")
        self.model = model_size

    async def transcribe(self, audio_bytes: bytes, language: str = "en", extension: str = ".wav") -> str:
        """
        Transcribes audio bytes to text using Groq Cloud API.
        """
        if not self.client or len(audio_bytes) < 1000:
            return "[Mock Transcription] Hello from cloud API."

        print(f"Transcribing {len(audio_bytes)} bytes using Groq API...")
        
        # Groq requires a file-like object with a filename
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
            
        try:
            with open(temp_audio_path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(temp_audio_path, file.read()),
                    model=self.model,
                    response_format="text",
                    language=language
                )
            os.remove(temp_audio_path)
            return transcription
        except Exception as e:
            print(f"Groq API Error: {e}")
            os.remove(temp_audio_path)
            return f"[Error transcribing: {str(e)}]"
