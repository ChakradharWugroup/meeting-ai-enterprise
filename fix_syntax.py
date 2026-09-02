import re

with open(r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\backend\api\fastapi.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('transcript = "No speech detected in this recording."`n        segments = []', 'transcript = "No speech detected in this recording."\n        segments = []')

with open(r'C:\Users\KalleChakradhar\Desktop\meeting_AI_report\meeting-ai-enterprise\backend\api\fastapi.py', 'w', encoding='utf-8') as f:
    f.write(text)
