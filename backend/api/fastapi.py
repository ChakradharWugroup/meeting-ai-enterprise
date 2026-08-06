from fastapi import FastAPI, HTTPException, status, Request, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
import subprocess
import asyncio

# Import our enterprise modules
from backend.streaming.audio_receiver import AudioReceiver
from backend.ai.whisper import WhisperTranscriber
from backend.ai.summarizer import MeetingSummarizer
from backend.teams.webhook import webhook_router
from backend.api.pdf_generator import generate_meeting_pdf
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from pydantic import BaseModel

scheduler = AsyncIOScheduler()
scheduler.start()

app = FastAPI(
    title="Enterprise AI Meeting Assistant API",
    description="API for live meeting transcription, streaming analysis, and intelligence generation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)

# In-memory storage for active streams (mocking)
active_receivers = {}
dynamic_meetings = []
transcriber = WhisperTranscriber()
summarizer = MeetingSummarizer()

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "meeting-ai-api"}

@app.post("/meeting/start", tags=["Meetings"])
async def start_meeting(meeting_id: str):
    receiver = AudioReceiver(meeting_id)
    await receiver.start_receiving()
    active_receivers[meeting_id] = receiver
    return {"message": f"Meeting {meeting_id} initialized successfully."}

@app.post("/meeting/{meeting_id}/stream", tags=["Meetings"])
async def receive_audio_stream(meeting_id: str, request: Request):
    if meeting_id not in active_receivers:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    chunk = await request.body()
    # Assuming timestamp is passed in headers for this mock
    timestamp = 0.0
    
    await active_receivers[meeting_id].ingest_audio_chunk(chunk, timestamp)
    return {"message": "Stream packet received."}

@app.websocket("/meeting/{meeting_id}/ws")
async def websocket_audio_endpoint(websocket: WebSocket, meeting_id: str):
    await websocket.accept()
    if meeting_id not in active_receivers:
        active_receivers[meeting_id] = AudioReceiver(meeting_id)
        await active_receivers[meeting_id].start_receiving()
    
    receiver = active_receivers[meeting_id]
    
    try:
        while True:
            # Receive binary audio chunk from the Playwright bot
            data = await websocket.receive_bytes()
            timestamp = 0.0
            await receiver.ingest_audio_chunk(data, timestamp)
    except WebSocketDisconnect:
        print(f"Client disconnected from meeting {meeting_id}")
        # Automatically transition the meeting to completed so UI updates!
        for m in dynamic_meetings:
            if m["id"] == meeting_id:
                m["status"] = "completed"
                break
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.post("/dispatch", tags=["Meetings"])
async def dispatch_bot(request: Request):
    """
    Spawns the Playwright headless bot in the background.
    Expected JSON: {"url": "https://teams.microsoft.com/..."}
    """
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing meeting URL")
        
    meeting_id = f"mtg-{hash(url) % 10000}"
    
    # Run the node script in the background
    bot_dir = "/app/teams-bot" if os.path.exists("/app/teams-bot") else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "teams-bot")
    
    import subprocess
    try:
        subprocess.Popen(
            ["node", "join_meeting.js", url, meeting_id],
            cwd=bot_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Add to our dynamic list so the UI updates instantly!
        dynamic_meetings.insert(0, {
            "id": meeting_id,
            "title": f"Live Session ({meeting_id[-4:]})",
            "status": "live",
            "participants": 1,
            "duration": "0m",
            "summary": "AI Notetaker has joined and is listening...",
            "sentiment": "Neutral"
        })
        
        return {"status": "success", "message": f"Bot dispatched to meeting {meeting_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ScheduleRequest(BaseModel):
    url: str
    scheduled_time: str # ISO format string

@app.post("/meeting/schedule", tags=["Meetings"])
async def schedule_meeting(req: ScheduleRequest):
    try:
        meeting_time = datetime.fromisoformat(req.scheduled_time.replace("Z", "+00:00"))
        meeting_id = f"mtg-{hash(req.url) % 10000}"
        
        def job_func(url_val, m_id):
            bot_dir = "/app/teams-bot" if os.path.exists("/app/teams-bot") else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "teams-bot")
            import subprocess
            subprocess.Popen(
                ["node", "join_meeting.js", url_val, m_id],
                cwd=bot_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Update status to live when bot actually joins
            for m in dynamic_meetings:
                if m["id"] == m_id:
                    m["status"] = "live"
                    m["summary"] = "AI Notetaker has joined and is listening..."
                    break
                    
        scheduler.add_job(job_func, 'date', run_date=meeting_time, args=[req.url, meeting_id])
        
        dynamic_meetings.insert(0, {
            "id": meeting_id,
            "title": f"Scheduled Session ({meeting_id[-4:]})",
            "status": "scheduled",
            "participants": 0,
            "duration": "0m",
            "summary": f"Scheduled for {meeting_time.strftime('%Y-%m-%d %H:%M')}",
            "sentiment": "Neutral"
        })
        
        return {"status": "success", "message": "Meeting scheduled successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_uploaded_file(file_path: str, meeting_id: str, filename: str):
    try:
        import glob
        
        # Extract and compress audio using ffmpeg to MP3 format in 30-minute chunks
        # This guarantees we NEVER hit Groq's 25MB limit even for 10-hour videos
        chunk_prefix = file_path + "_chunk_"
        print(f"Extracting and chunking audio from {file_path}")
        
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", file_path, 
            "-vn", "-acodec", "libmp3lame", "-b:a", "32k", "-ar", "16000", "-ac", "1",
            "-f", "segment", "-segment_time", "1800", f"{chunk_prefix}%03d.mp3",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        if proc.returncode != 0:
            raise Exception("ffmpeg failed to process video")
        
        # Find all generated chunks
        chunks = sorted(glob.glob(f"{chunk_prefix}*.mp3"))
        
        full_transcript_text = ""
        all_segments = []
        current_speaker = "Speaker A"
        last_end_time = 0.0
        
        for i, chunk_path in enumerate(chunks):
            print(f"Transcribing chunk {i+1}/{len(chunks)}: {chunk_path}")
            with open(chunk_path, "rb") as f:
                audio_bytes = f.read()
            
            transcript_res = await transcriber.transcribe(audio_bytes, extension=".mp3")
            
            if isinstance(transcript_res, dict):
                text = transcript_res.get("text", "")
                segments = transcript_res.get("segments", [])
            else:
                text = getattr(transcript_res, "text", "")
                segments = getattr(transcript_res, "segments", [])
                
            full_transcript_text += text + " "
            chunk_offset = i * 1800 # 30 minutes in seconds
            
            for seg in segments:
                if isinstance(seg, dict):
                    start = seg.get("start", 0.0) + chunk_offset
                    end = seg.get("end", 0.0) + chunk_offset
                    seg_text = seg.get("text", "").strip()
                else:
                    start = getattr(seg, "start", 0.0) + chunk_offset
                    end = getattr(seg, "end", 0.0) + chunk_offset
                    seg_text = getattr(seg, "text", "").strip()
                    
                if not seg_text: continue
                    
                # Heuristic: swap speaker if gap > 1.5s
                if start - last_end_time > 1.5:
                    current_speaker = "Speaker B" if current_speaker == "Speaker A" else "Speaker A"
                    
                all_segments.append({
                    "speaker": current_speaker,
                    "start": start,
                    "end": end,
                    "text": seg_text
                })
                last_end_time = end
            
        print(f"Transcription complete. Total length: {len(full_transcript_text)}")
        
        # We need a string summary from the model
        summary = "Uploaded Recording Transcript:\n\n" + full_transcript_text.strip()
        
        # Add to completed meetings
        dynamic_meetings.insert(0, {
            "id": meeting_id,
            "title": f"Uploaded: {filename}",
            "status": "completed",
            "participants": 2,
            "duration": f"{len(chunks) * 30}m approx",
            "summary": summary[:200] + "...",
            "sentiment": "Neutral",
            "full_transcript": full_transcript_text,
            "segments": all_segments
        })
        
        # Cleanup
        os.remove(file_path)
        for chunk_path in chunks:
            os.remove(chunk_path)
            
        print(f"Upload {meeting_id} processed successfully.")
    except Exception as e:
        print(f"Error processing upload {meeting_id}: {e}")
        # Clean up if failed
        if os.path.exists(file_path): os.remove(file_path)
        import glob
        for chunk in glob.glob(file_path + "_chunk_*.mp3"):
            os.remove(chunk)

@app.post("/meeting/upload", tags=["Meetings"])
async def upload_meeting_recording(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        meeting_id = f"up-{hash(file.filename) % 10000}"
        
        # Save to temp file
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
        with os.fdopen(fd, 'wb') as f:
            shutil.copyfileobj(file.file, f)
            
        # Add a "processing" entry so the UI sees it in active sessions!
        dynamic_meetings.insert(0, {
            "id": meeting_id,
            "title": f"Processing: {file.filename}",
            "status": "live",
            "participants": 1,
            "duration": "0m",
            "summary": "Extracting audio and crunching AI transcript...",
            "sentiment": "Processing"
        })
            
        background_tasks.add_task(process_uploaded_file, temp_path, meeting_id, file.filename)
        return {"status": "success", "message": "File uploaded and processing started in background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/meetings", tags=["Meetings"])
async def list_meetings():
    # Return mock meetings to populate the premium UI dashboard
    mock_meetings = [
        {
            "id": "mtg-101",
            "title": "Q3 Architecture Review",
            "status": "live",
            "participants": 4,
            "duration": "45m",
            "summary": "Discussing the transition to Docker and open source models.",
            "sentiment": "Positive"
        },
        {
            "id": "mtg-102",
            "title": "Marketing Sync",
            "status": "completed",
            "participants": 6,
            "duration": "1h 12m",
            "summary": "Aligned on the new ad campaign launch dates. Need assets from design.",
            "sentiment": "Neutral"
        },
        {
            "id": "mtg-103",
            "title": "Weekly Engineering Standup",
            "status": "completed",
            "participants": 12,
            "duration": "25m",
            "summary": "Blockers reported on the API integration. Resolving via pair programming.",
            "sentiment": "Positive"
        }
    ]
    return dynamic_meetings + mock_meetings

@app.get("/meeting/{meeting_id}/summary", tags=["Meetings"])
async def get_meeting_summary(meeting_id: str):
    # This would typically fetch from the Postgres DB via SQLAlchemy
    return {
        "meeting_id": meeting_id,
        "summary": "This is a live updating summary...",
        "action_items": [{"description": "Finish API", "owner": "AI"}]
    }

@app.get("/meeting/{meeting_id}/pdf", tags=["Meetings"])
async def download_meeting_pdf(meeting_id: str):
    # Find the meeting details from the mock data
    meeting = next((m for m in dynamic_meetings if m["id"] == meeting_id), None)
    
    title = meeting["title"] if meeting else f"Meeting {meeting_id}"
    summary = meeting["summary"] if meeting else "AI Notetaker generated summary."
    transcript = meeting.get("full_transcript", "")
    segments = meeting.get("segments", [])
    
    pdf_buffer = generate_meeting_pdf(title, summary, transcript, segments)
    
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"Transcript_{current_time}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.fastapi:app", host="0.0.0.0", port=8000, reload=True)
