import os

file_path = r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\backend\api\fastapi.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the transcript reconstruction to include speaker labels and timestamps
old_reconstruct = """            # Reconstruct the full transcript text
            full_transcript_text = "\\n".join([seg["text"] for seg in all_segments])"""

new_reconstruct = """            # Reconstruct the full transcript text with SPEAKER DIARIZATION (Voice Biometrics)
            def format_time(seconds):
                m, s = divmod(int(seconds), 60)
                h, m = divmod(m, 60)
                if h > 0: return f"{h:02d}:{m:02d}:{s:02d}"
                return f"{m:02d}:{s:02d}"
                
            formatted_lines = []
            for seg in all_segments:
                speaker = seg.get("speaker", "Speaker")
                start_str = format_time(seg.get("start", 0))
                end_str = format_time(seg.get("end", 0))
                text = seg.get("text", "")
                formatted_lines.append(f"{speaker} [{start_str} - {end_str}]:\\n{text}\\n")
            
            full_transcript_text = "\\n".join(formatted_lines).strip()"""

content = content.replace(old_reconstruct, new_reconstruct)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed transcript reconstruction to include Speaker Diarization.')
