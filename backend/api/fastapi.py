from fastapi import FastAPI, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os

# Import our enterprise modules
from backend.streaming.audio_receiver import AudioReceiver
from backend.ai.whisper import WhisperTranscriber
from backend.ai.summarizer import MeetingSummarizer
from backend.teams.webhook import webhook_router
from backend.api.pdf_generator import generate_meeting_pdf
from fastapi.responses import StreamingResponse

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
    transcript = "" # We'll use the default mock in the pdf generator
    
    pdf_buffer = generate_meeting_pdf(title, summary, transcript)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=meeting_{meeting_id}_report.pdf"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.fastapi:app", host="0.0.0.0", port=8000, reload=True)
