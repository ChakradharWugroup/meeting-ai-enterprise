import os
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv; load_dotenv(); HF_TOKEN = os.getenv("HF_TOKEN", "")

class PyannoteDiarizer:
    def __init__(self):
        pass

    def diarize(self, audio_path: str):
        try:
            print("Initializing Pyannote Speaker Diarization model on-demand...")
            from pyannote.audio import Pipeline
            import torch
            from pydub import AudioSegment
            import numpy as np
            
            print(f"Running pyannote diarization on {audio_path}...")
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=HF_TOKEN)
            
            if torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
            else:
                pipeline.to(torch.device("cpu"))
                
            audio_segment = AudioSegment.from_file(audio_path)
            audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
            
            sample_rate = audio_segment.frame_rate
            samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
            samples = samples / 32768.0
            
            waveform = torch.from_numpy(samples).unsqueeze(0)
            
            diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})
            
            if hasattr(diarization, "speaker_diarization"):
                diarization = diarization.speaker_diarization
                
            diarization_turns = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker.startswith("SPEAKER_"):
                    try:
                        spk_id = int(speaker.split("_")[1])
                        if spk_id < 26:
                            speaker = f"Speaker {chr(65 + spk_id)}"
                        else:
                            speaker = f"Speaker {spk_id + 1}"
                    except:
                        pass
                
                diarization_turns.append({
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": speaker
                })
            
            # Explicitly delete pipeline and free GPU memory to prevent OOM
            del pipeline
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            return diarization_turns
        except Exception as e:
            print(f"Diarization error: {e}")
            import traceback
            traceback.print_exc()
            return []

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
