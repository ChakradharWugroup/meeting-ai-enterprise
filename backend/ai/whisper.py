import os
import tempfile
import asyncio

class WhisperTranscriber:
    def __init__(self):
        pass

    async def transcribe(self, audio_bytes: bytes, language: str = "en", extension: str = ".wav") -> dict:
        """
        Transcribes audio bytes to text using Local Whisper AI on GPU.
        Initializes on-demand to prevent CUDA context pollution.
        """
        if len(audio_bytes) < 1000:
            return {"text": "", "segments": []}

        print(f"Transcribing {len(audio_bytes)} bytes locally on GPU...")
        
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
            
        try:
            # Whisper run is CPU/GPU blocking, wrap in asyncio.to_thread
            def run_whisper():
                import whisper
                import torch
                print("Loading Whisper model on demand...")
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model = whisper.load_model("base", device=device)
                res = model.transcribe(temp_audio_path, language=language)
                del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                return res
                
            result = await asyncio.to_thread(run_whisper)
            os.remove(temp_audio_path)
            
            return result
        except Exception as e:
            print(f"Local Whisper Error: {e}")
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
            return {"text": f"[Error transcribing: {str(e)}]", "segments": []}
