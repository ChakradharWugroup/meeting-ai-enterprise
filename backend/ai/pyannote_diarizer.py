import os

HF_TOKEN = os.getenv("HF_TOKEN", "")

class PyannoteDiarizer:
    def __init__(self):
        self.pipeline = None
        
    def _init_pipeline(self):
        if self.pipeline is not None:
            return
            
        print("Initializing Pyannote Speaker Diarization model (this requires significant RAM)...")
        try:
            from pyannote.audio import Pipeline
            import torch
            
            # Use GPU if available, else CPU
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=HF_TOKEN)
            if self.pipeline:
                self.pipeline.to(device)
            else:
                print("WARNING: Pyannote pipeline could not be loaded. Are you sure the HF_TOKEN has access to the gated model?")
        except Exception as e:
            print(f"Failed to load Pyannote pipeline: {e}")

    def diarize(self, audio_path: str):
        self._init_pipeline()
        
        if not self.pipeline:
            raise Exception("Pyannote pipeline is not initialized (Missing HF_TOKEN or Insufficient RAM)")
        
        print(f"Running true biometric diarization on {audio_path}...")
        diarization = self.pipeline(audio_path)
        
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "start": turn.start,
                "end": turn.end,
                "speaker": speaker
            })
        return segments

    def align_whisper_pyannote(self, whisper_segments: list, pyannote_segments: list, chunk_offset: float = 0.0):
        """
        Aligns Groq Whisper text segments with Pyannote biometric segments based on maximum timestamp overlap.
        """
        aligned_segments = []
        for w_seg in whisper_segments:
            # Handle groq dict vs object
            if isinstance(w_seg, dict):
                w_start = w_seg.get("start", 0.0) + chunk_offset
                w_end = w_seg.get("end", 0.0) + chunk_offset
                w_text = w_seg.get("text", "").strip()
            else:
                w_start = getattr(w_seg, "start", 0.0) + chunk_offset
                w_end = getattr(w_seg, "end", 0.0) + chunk_offset
                w_text = getattr(w_seg, "text", "").strip()
                
            if not w_text: continue
            
            # Find pyannote segment with maximum overlap
            best_speaker = "Speaker A"
            max_overlap = 0.0
            
            for p_seg in pyannote_segments:
                # pyannote_segments are absolute to the chunk, so we add chunk_offset
                p_start = p_seg["start"] + chunk_offset
                p_end = p_seg["end"] + chunk_offset
                
                overlap_start = max(w_start, p_start)
                overlap_end = min(w_end, p_end)
                overlap = max(0.0, overlap_end - overlap_start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = p_seg["speaker"].replace("SPEAKER_", "Speaker ")
                    # If it's something like Speaker 00, format it nicely
                    if "00" in best_speaker: best_speaker = "Speaker A"
                    elif "01" in best_speaker: best_speaker = "Speaker B"
                    elif "02" in best_speaker: best_speaker = "Speaker C"
                    elif "03" in best_speaker: best_speaker = "Speaker D"
                    
            aligned_segments.append({
                "start": w_start,
                "end": w_end,
                "speaker": best_speaker,
                "text": w_text
            })
        return aligned_segments
