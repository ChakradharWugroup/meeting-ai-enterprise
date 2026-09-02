"""
Meeting AI Enterprise - Cloud FastAPI Backend
Uses Gemini API exclusively for transcription and summarization.
Uses SQLite instead of PostgreSQL (no extra DB container needed).
"""
import os
import uuid
import shutil
import tempfile
import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import aiofiles

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ?€?€?€ Database (SQLite) ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
DB_PATH = os.environ.get("DB_PATH", "/app/data/meetings.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class MeetingRecord(Base):
    __tablename__ = "meetings"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String, default="Untitled Meeting")
    status      = Column(String, default="Pending")   # Pending, Processing, Completed, Error
    created_at  = Column(String)
    duration    = Column(Float, default=0.0)
    participants= Column(Integer, default=0)
    sentiment   = Column(String, default="Neutral")
    transcript  = Column(Text, default="[]")          # JSON list of segments
    summary     = Column(Text, default="")
    tokens_used = Column(Integer, default=0)
    error_msg   = Column(String, default="")
    pdf_path    = Column(String, default="")
    process_time= Column(Float, default=0.0)

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# ?€?€?€ App ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
app = FastAPI(title="Meeting AI Cloud API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ?€?€?€ Helpers ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _meeting_to_dict(m: MeetingRecord) -> dict:
    h = int(m.duration // 3600)
    mn = int((m.duration % 3600) // 60)
    s  = int(m.duration % 60)
    dur_str = f"{h:02d}:{mn:02d}:{s:02d}" if m.duration else "00:00:00"
    return {
        "id":           m.id,
        "title":        m.title,
        "status":       m.status,
        "date":         m.created_at,
        "duration":     dur_str,
        "participants": m.participants,
        "sentiment":    m.sentiment,
        "summary":      m.summary,
        "tokens_used":  m.tokens_used,
        "process_time": m.process_time,
        "error_message":m.error_msg,
    }

# ?€?€?€ Background processing ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
async def process_file_with_gemini(file_path: str, meeting_id: int, api_key: str):
    """Full pipeline: extract audio ??Gemini transcribe ??Gemini summarize ??save"""
    import time
    start = time.time()

    db = SessionLocal()
    meeting = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
    meeting.status = "Processing"
    db.commit()
    db.close()

    try:
        # 1. Extract audio to mp3 using ffmpeg
        audio_path = str(UPLOAD_DIR / f"audio_{meeting_id}.mp3")
        probe_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = 0.0
        try:
            probe_data = json.loads(probe_result.stdout)
            duration = float(probe_data.get("format", {}).get("duration", 0))
        except Exception:
            pass

        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, "-vn", "-acodec", "libmp3lame", "-q:a", "4", audio_path],
            capture_output=True
        )

        # 2. Transcribe + Diarize with Gemini
        from backend.ai.gemini_transcriber import GeminiTranscriber
        transcriber = GeminiTranscriber(api_key=api_key)
        segments, tokens = await transcriber.transcribe_and_diarize(audio_path)

        # Count unique speakers
        speakers = set(s.get("speaker", "") for s in segments)

        # 3. Summarize with Gemini
        from backend.ai.gemini_ai import GeminiTranscriber as GeminiSummarizer
        summarizer = GeminiSummarizer(api_key=api_key)
        summary = await summarizer.summarize(segments)

        # 4. Generate PDF
        from backend.api.pdf_generator import generate_transcript_pdf
        pdf_name = f"meeting_{meeting_id}_transcript.pdf"
        pdf_path = str(OUTPUT_DIR / pdf_name)
        generate_transcript_pdf(segments, pdf_path)

        elapsed = time.time() - start

        db = SessionLocal()
        meeting = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
        meeting.status       = "Completed"
        meeting.transcript   = json.dumps(segments)
        meeting.summary      = summary if isinstance(summary, str) else json.dumps(summary)
        meeting.tokens_used  = tokens
        meeting.participants = len(speakers)
        meeting.duration     = duration
        meeting.process_time = round(elapsed, 1)
        meeting.pdf_path     = pdf_path
        meeting.sentiment    = "Neutral"
        db.commit()
        db.close()

        # Cleanup temp files
        for f in [file_path, audio_path]:
            try:
                os.remove(f)
            except Exception:
                pass

    except Exception as e:
        db = SessionLocal()
        meeting = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
        meeting.status   = "Error"
        meeting.error_msg = str(e)
        db.commit()
        db.close()
        print(f"Pipeline error for meeting {meeting_id}: {e}")


# ?€?€?€ Routes ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
@app.get("/health")
async def health():
    return {"status": "ok", "service": "meeting-ai-cloud", "model": GEMINI_MODEL}

@app.get("/meetings")
async def list_meetings():
    db = SessionLocal()
    meetings = db.query(MeetingRecord).order_by(MeetingRecord.id.desc()).all()
    db.close()
    return [_meeting_to_dict(m) for m in meetings]

@app.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: int):
    db = SessionLocal()
    m = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
    db.close()
    if not m:
        raise HTTPException(status_code=404, detail="Meeting not found")
    result = _meeting_to_dict(m)
    try:
        result["transcript"] = json.loads(m.transcript) if m.transcript else []
    except Exception:
        result["transcript"] = []
    return result

@app.post("/upload")
async def upload_meeting(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    meeting_name: Optional[str] = None,
    gemini_key: Optional[str] = None
):
    api_key = gemini_key or GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY is required")

    # Save the uploaded file
    ext = Path(file.filename).suffix
    temp_path = str(UPLOAD_DIR / f"upload_{uuid.uuid4().hex}{ext}")
    async with aiofiles.open(temp_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Create DB record
    db = SessionLocal()
    name = meeting_name or file.filename
    record = MeetingRecord(
        title=name,
        status="Pending",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    meeting_id = record.id
    db.close()

    # Start background processing
    background_tasks.add_task(process_file_with_gemini, temp_path, meeting_id, api_key)

    return {"status": "success", "meeting_id": meeting_id, "message": "Processing started with Gemini"}

@app.get("/meetings/{meeting_id}/pdf")
async def download_pdf(meeting_id: int):
    db = SessionLocal()
    m = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
    db.close()
    if not m or not m.pdf_path or not os.path.exists(m.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(m.pdf_path, media_type="application/pdf", filename=f"meeting_{meeting_id}.pdf")

@app.post("/dispatch")
async def dispatch_bot(request: Request):
    """For cloud: Teams bot dispatch is not available. Return informative message."""
    return JSONResponse(
        status_code=200,
        content={"status": "cloud_only", "message": "Teams bot dispatching is only available on the local office server. Please upload a recording file instead."}
    )


async def process_youtube_bg(url: str, meeting_id: int, api_key: str):
    import subprocess
    import tempfile
    import uuid
    import asyncio
    
    db = SessionLocal()
    record = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
    
    try:
        if record:
            record.status = "Downloading YouTube Audio"
            db.commit()
            
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"yt_{uuid.uuid4().hex}.m4a")
        
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "-f", "bestaudio[ext=m4a]/best", "-o", temp_path, url,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        if not os.path.exists(temp_path):
            raise Exception("Failed to download audio")
            
        if record:
            record.status = "Processing Audio"
            db.commit()
            
        await process_file_with_gemini(temp_path, meeting_id, api_key)
        
    except Exception as e:
        if record:
            record.status = f"Error: {str(e)}"
            db.commit()
    finally:
        db.close()

@app.post("/youtube")
async def transcribe_youtube_new(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    url = data.get("url", "")
    api_key = data.get("gemini_key") or GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY is required")
    if not url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")
        
    db = SessionLocal()
    record = MeetingRecord(
        title=f"YouTube: {url.split('v=')[-1][:11] if 'v=' in url else 'Video'}",
        status="Pending",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    m_id = record.id
    db.close()
    
    background_tasks.add_task(process_youtube_bg, url, m_id, api_key)
    
    return {"status": "success", "message": "YouTube notetaker dispatched"}

from fastapi import Form
import shutil

@app.post("/upload-chunk")
async def upload_chunk(
    background_tasks: BackgroundTasks,
    chunk: UploadFile = File(...),
    file_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...)
):
    temp_path = str(UPLOAD_DIR / f"chunked_{file_id}")
    with open(temp_path, "ab") as f:
        f.write(await chunk.read())
        
    if chunk_index == total_chunks - 1:
        db = SessionLocal()
        record = MeetingRecord(
            title=filename,
            status="Processing",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        m_id = record.id
        db.close()
        
        background_tasks.add_task(process_file_with_gemini, temp_path, m_id, GEMINI_API_KEY)
        return {"status": "success", "message": "All chunks received."}
    return {"status": "success", "message": f"Chunk {chunk_index+1}/{total_chunks} received."}
