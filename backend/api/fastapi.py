from fastapi import FastAPI, HTTPException, status, Request, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import re
import time
import shutil
import tempfile
import subprocess
import asyncio

# Import our enterprise modules
from backend.streaming.audio_receiver import AudioReceiver
from backend.ai.whisper import WhisperTranscriber
from backend.ai.whisper import WhisperTranscriber
from backend.ai.deepgram_ai import DeepgramAI
from backend.ai.pyannote_diarizer import PyannoteDiarizer
from backend.ai.summarizer import MeetingSummarizer
from backend.teams.webhook import webhook_router
from backend.api.pdf_generator import generate_transcript_pdf
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from pydantic import BaseModel

scheduler = AsyncIOScheduler()

app = FastAPI(
    title="Enterprise AI Meeting Assistant API",
    description="API for live meeting transcription, streaming analysis, and intelligence generation",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    scheduler.start()
    print("APScheduler started successfully.")

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
# Initialize AI modules
from backend.ai.whisper import WhisperTranscriber
from backend.ai.deepgram_ai import DeepgramAI
from backend.ai.pyannote_diarizer import PyannoteDiarizer
from backend.ai.summarizer import MeetingSummarizer
from backend.ai.gemini_ai import GeminiTranscriber

transcriber = WhisperTranscriber()
deepgram_client = DeepgramAI()
pyannote_client = PyannoteDiarizer()
summarizer = MeetingSummarizer()

os.environ["GEMINI_API_KEY"] = "REDACTED"
gemini_client = GeminiTranscriber()

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
        print(f"[{meeting_id}] Bot/Client disconnected from meeting WebSocket.")
    except Exception as e:
        print(f"[{meeting_id}] WebSocket error: {e}")
    finally:
        await receiver.stop_receiving()
        audio_data = bytes(receiver.full_audio)
        if len(audio_data) > 0:
            print(f"[{meeting_id}] Captured {len(audio_data)} bytes of audio. Triggering transcription pipeline...")
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"{meeting_id}_teams.webm")
            with open(temp_path, "wb") as f:
                f.write(audio_data)
                
            for m in dynamic_meetings:
                if m["id"] == meeting_id:
                    m["status"] = "live"
                    m["sentiment"] = "Processing"
                    m["summary"] = "Audio captured. Extracting and transcribing with AI..."
                    break
                    
            asyncio.create_task(process_uploaded_file(temp_path, meeting_id, f"Teams Session ({meeting_id[-4:]})"))
        else:
            print(f"[{meeting_id}] Disconnected without audio data.")
            for m in dynamic_meetings:
                if m["id"] == meeting_id:
                    m["status"] = "completed"
                    m["summary"] = "Session ended (No audio was captured before bot exited)."
                    m["sentiment"] = "Neutral"
                    break
                    
        if meeting_id in active_receivers:
            del active_receivers[meeting_id]

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
        
    import uuid
    meeting_id = f"mtg-{uuid.uuid4().hex[:6]}"
    
    # Run the node script in the background
    bot_dir = "/app/teams-bot" if os.path.exists("/app/teams-bot") else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "teams-bot")
    
    import subprocess
    try:
        subprocess.Popen(
            ["node", "join_meeting.js", url, meeting_id, f"ws://127.0.0.1:{request.url.port or 8081}/meeting/{meeting_id}/ws"],
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

async def process_uploaded_file(file_path: str, meeting_id: str, filename: str, pre_timings: dict = None, start_time: float = None):
    t_start = start_time or time.time()
    try:
        import glob
        import shutil
        
        # Make absolutely sure the file_path is completely ASCII safe to prevent any Gemini upload crashes
        safe_file_path = os.path.join(os.path.dirname(file_path), f"safe_{meeting_id}_audio.tmp")
        if file_path != safe_file_path and os.path.exists(file_path):
            shutil.move(file_path, safe_file_path)
            file_path = safe_file_path
        
        full_transcript_text = ""
        all_segments = []
        tokens_used = 0
        
        t_extract_start = time.time()
        
        if True:
            # UNIFIED PIPELINE: Gemini 3.5 Flash Lite Native Diarization & Transcription with Chunking
            chunk_prefix = file_path + "_chunk_"
            print(f"Extracting and chunking audio from {file_path} into 3-minute segments for Gemini...")
            
            def run_ffmpeg_chunk():
                return subprocess.run([
                    "ffmpeg", "-y", "-i", file_path, 
                    "-vn", "-acodec", "libmp3lame", "-b:a", "32k", "-ar", "16000", "-ac", "1",
                    "-f", "segment", "-segment_time", "180", f"{chunk_prefix}%03d.mp3"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            loop = asyncio.get_event_loop()
            proc = await loop.run_in_executor(None, run_ffmpeg_chunk)
            
            if proc.returncode != 0:
                raise Exception("ffmpeg failed to process audio for Gemini chunking")
            
            t_extract_end = time.time()
            t_ai_start = time.time()
            
            # Process each chunk sequentially
            chunks = sorted(glob.glob(f"{chunk_prefix}*.mp3"))
            print(f"Total chunks generated: {len(chunks)}")
            
            for i, chunk_path in enumerate(chunks):
                print(f"Calling Gemini API for chunk {i+1}/{len(chunks)}: {chunk_path}")
                try:
                    res = await gemini_client.transcribe_and_diarize(chunk_path)
                    
                    # Offset the timestamps by 3 minutes (180 seconds) per chunk
                    chunk_offset = i * 180
                    for seg in res["segments"]:
                        seg["start"] += chunk_offset
                        seg["end"] += chunk_offset
                        all_segments.append(seg)
                except Exception as e:
                    print(f"Warning: Gemini processing failed for chunk {i+1}: {e}")
                finally:
                    # Clean up local chunk
                    try:
                        os.remove(chunk_path)
                    except:
                        pass
                        
            t_ai_end = time.time()
            
            # Reconstruct the full transcript text with SPEAKER DIARIZATION (Voice Biometrics)
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
                formatted_lines.append(f"{speaker} [{start_str} - {end_str}]:\n{text}\n")
            
            full_transcript_text = "\n".join(formatted_lines).strip()
            
            # Estimate tokens for UI display
            tokens_used = int(len(full_transcript_text.split()) * 1.35)
                
        print(f"Transcription complete. Total length: {len(full_transcript_text)}")
        
        # Calculate step timings
        t_extract_sec = round(t_extract_end - t_extract_start, 1)
        t_ai_sec = round(t_ai_end - t_ai_start, 1)
        total_time_sec = round(time.time() - t_start, 1)
        
        steps = []
        if pre_timings:
            for k, v in pre_timings.items():
                steps.append(f"{k}: {v}")
        steps.append(f"Audio Extract: {t_extract_sec}s")
        steps.append(f"AI Transcribe: {t_ai_sec}s")
        step_timings_str = " ??".join(steps)
        
        # We need a string summary from the model
        summary = "Uploaded Recording Transcript:\n\n" + full_transcript_text.strip()
        
        # Add to completed meetings
        duration_display = "N/A"
        if all_segments:
            duration_s = all_segments[-1]["end"]
            duration_display = f"{int(duration_s // 60)}m {int(duration_s % 60)}s"
            
        # Update existing placeholder or insert new
        updated = False
        for m in dynamic_meetings:
            if m["id"] == meeting_id:
                m["status"] = "completed"
                m["title"] = f"Uploaded: {filename}"
                m["participants"] = 2
                m["duration"] = duration_display
                m["summary"] = summary[:200] + "..."
                m["sentiment"] = "Neutral"
                m["full_transcript"] = full_transcript_text
                m["segments"] = all_segments
                m["tokens_used"] = f"{tokens_used:,} tokens"
                m["processing_time"] = f"{total_time_sec}s"
                m["step_timings"] = step_timings_str
                updated = True
                break
                
        if not updated:
            dynamic_meetings.insert(0, {
                "id": meeting_id,
                "title": f"Uploaded: {filename}",
                "status": "completed",
                "participants": 2,
                "duration": duration_display,
                "summary": summary[:200] + "...",
                "sentiment": "Neutral",
                "full_transcript": full_transcript_text,
                "segments": all_segments,
                "tokens_used": f"{tokens_used:,} tokens",
                "processing_time": f"{total_time_sec}s",
                "step_timings": step_timings_str
            })
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        for chunk in glob.glob(file_path + "_chunk_*.mp3"):
            os.remove(chunk)
            
        print(f"Upload {meeting_id} processed successfully.")
    except Exception as e:
        error_msg = f"Error processing upload: {str(e)}"
        print(f"{error_msg} for {meeting_id}")
        
        # Update UI to show the error
        for m in dynamic_meetings:
            if m["id"] == meeting_id:
                m["status"] = "completed"
                m["summary"] = error_msg
                m["full_transcript"] = error_msg
                break
                
        # Clean up if failed
        if os.path.exists(file_path): os.remove(file_path)
        import glob
        for chunk in glob.glob(file_path + "_chunk_*.mp3"):
            os.remove(chunk)

from fastapi import Form
chunk_storage = {}

@app.post("/upload-chunk", tags=["Meetings"])
async def upload_chunk(
    background_tasks: BackgroundTasks,
    chunk: UploadFile = File(...),
    file_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...)
):
    try:
        import tempfile
        # Create directory for temp storage if needed
        upload_dir = os.path.join(tempfile.gettempdir(), "meeting_ai_uploads")
        os.makedirs(upload_dir, exist_ok=True)
        temp_path = os.path.join(upload_dir, file_id)
        
        # We append to the temp file
        # Note: In a production system, we'd ensure chunks arrive in order or write to specific offsets.
        # Since the frontend will send them sequentially, appending is fine.
        with open(temp_path, "ab") as f:
            shutil.copyfileobj(chunk.file, f)
            
        if chunk_index == total_chunks - 1:
            # Final chunk received
            meeting_id = f"up-{hash(filename) % 10000}"
            dynamic_meetings.insert(0, {
                "id": meeting_id,
                "title": f"Processing: {filename}",
                "status": "live",
                "participants": 1,
                "duration": "0m",
                "summary": "Extracting audio and crunching AI transcript...",
                "sentiment": "Processing"
            })
            background_tasks.add_task(process_uploaded_file, temp_path, meeting_id, filename)
            return {"status": "success", "message": "All chunks received. Processing started."}
            
        return {"status": "success", "message": f"Chunk {chunk_index+1}/{total_chunks} received."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            "sentiment": "Neutral",
            "tokens_used": "1,840 tokens",
            "processing_time": "4.6s",
            "step_timings": "Audio: 1.8s ??AI Transcribe: 2.8s"
        },
        {
            "id": "mtg-103",
            "title": "Weekly Engineering Standup",
            "status": "completed",
            "participants": 12,
            "duration": "25m",
            "summary": "Blockers reported on the API integration. Resolving via pair programming.",
            "sentiment": "Positive",
            "tokens_used": "3,420 tokens",
            "processing_time": "7.2s",
            "step_timings": "Audio: 2.1s ??AI Transcribe: 5.1s"
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
@app.get("/meetings/{meeting_id}/pdf", tags=["Meetings"])
async def download_meeting_pdf(meeting_id: str):
    # Find the meeting in dynamic_meetings
    meeting = next((m for m in dynamic_meetings if m["id"] == meeting_id), None)

    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting '{meeting_id}' not found. It may have expired after a server restart.")

    title = meeting.get("title", f"Meeting {meeting_id}")
    transcript = meeting.get("full_transcript", "")
    segments = meeting.get("segments", [])

    if not transcript and not segments:
        transcript = "No speech detected in this recording."
        segments = []

    pdf_buffer = generate_transcript_pdf(title, transcript, segments)

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', title[:40])
    filename = f"Transcript_{safe_title}_{current_time}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.fastapi:app", host="0.0.0.0", port=8000, reload=True)
async def process_youtube_url(url: str, meeting_id: str):
    import os, tempfile, json, subprocess, glob, re

    def update_status(msg: str):
        print(f"[{meeting_id}] Status update: {msg}")
        for m in dynamic_meetings:
            if m["id"] == meeting_id:
                m["summary"] = msg
                break

    loop = asyncio.get_event_loop()
    temp_dir = tempfile.gettempdir()
    start_total_time = time.time()

    try:
        # ?€?€ Step 1: Fetch video metadata (title + available subtitles) ?€?€?€?€?€?€?€?€?€?€
        update_status("Inspecting video for subtitles and title...")
        t_meta_start = time.time()

        def run_dump_json():
            return subprocess.run(
                ["yt-dlp", "--js-runtimes", "node", "--remote-components", "ejs:github", "--dump-json", url],
                capture_output=True
            )

        result_info = await loop.run_in_executor(None, run_dump_json)
        t_meta_sec = round(time.time() - t_meta_start, 1)

        filename = "YouTube_Video"
        available_subs = {}       # manual subs  {lang_code: [...]}
        available_auto_subs = {}  # auto-generated subs

        if result_info.returncode == 0 and result_info.stdout:
            try:
                first_line = result_info.stdout.decode(errors="replace").strip().split('\n')[0]
                info = json.loads(first_line)
                filename = info.get("title", "YouTube_Video")
                available_subs = info.get("subtitles", {})
                available_auto_subs = info.get("automatic_captions", {})

                for m in dynamic_meetings:
                    if m["id"] == meeting_id:
                        m["title"] = f"YouTube: {filename}"
                        break
            except Exception as e:
                print(f"Failed to parse yt-dlp JSON: {e}")

        # ?€?€ Step 2: Detect the video's primary spoken language ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
        spoken_lang = None
        if result_info.returncode == 0 and result_info.stdout:
            try:
                first_line = result_info.stdout.decode(errors="replace").strip().split('\n')[0]
                info_check = json.loads(first_line)
                spoken_lang = info_check.get("language")  # e.g. "zh-Hans", "en", "ms"
                if spoken_lang:
                    spoken_lang_base = spoken_lang.split('-')[0]
                    print(f"[{meeting_id}] Detected spoken language: {spoken_lang} (base: {spoken_lang_base})")
            except Exception as e:
                print(f"Failed to detect language: {e}")

        # ?€?€ Step 3: Try to use subtitles ONLY in the spoken language ?€?€?€?€?€?€?€?€?€?€?€?€?€
        subtitle_lang = None
        available_subs = {}
        available_auto_subs = {}
        use_auto = False

        def find_lang_in_subs(subs_dict, lang_code):
            if not lang_code:
                return None
            base = lang_code.split('-')[0]
            if lang_code in subs_dict:
                return lang_code
            if base in subs_dict:
                return base
            for key in subs_dict:
                if key.startswith(base):
                    return key
            return None

        if available_subs and spoken_lang:
            match = find_lang_in_subs(available_subs, spoken_lang)
            if match:
                subtitle_lang = match
                use_auto = False
                update_status(f"Found manual subtitles in spoken language '{subtitle_lang}'. Extracting...")

        if not subtitle_lang and available_auto_subs and spoken_lang:
            match = find_lang_in_subs(available_auto_subs, spoken_lang)
            if match:
                subtitle_lang = match
                use_auto = True
                update_status(f"Found auto-generated subtitles in spoken language '{subtitle_lang}'. Extracting...")

        if not subtitle_lang:
            if available_subs:
                subtitle_lang = next(iter(available_subs))
                use_auto = False
                update_status(f"Using available subtitles in '{subtitle_lang}'...")
            elif available_auto_subs:
                subtitle_lang = next(iter(available_auto_subs))
                use_auto = True
                update_status(f"Using auto-generated subtitles in '{subtitle_lang}'...")

        if subtitle_lang:
            sub_output = os.path.join(temp_dir, f"{meeting_id}_sub")
            sub_flag = "--write-auto-subs" if use_auto else "--write-subs"
            t_sub_start = time.time()

            def run_sub_download():
                return subprocess.run(
                    [
                        "yt-dlp", "--js-runtimes", "node",
                        sub_flag,
                        "--sub-lang", subtitle_lang,
                        "--sub-format", "vtt",
                        "--skip-download",
                        "-o", sub_output,
                        url
                    ],
                    capture_output=True
                )

            await loop.run_in_executor(None, run_sub_download)
            t_sub_sec = round(time.time() - t_sub_start, 1)

            sub_files = glob.glob(os.path.join(temp_dir, f"{meeting_id}_sub*.vtt")) + \
                        glob.glob(os.path.join(temp_dir, f"{meeting_id}_sub*.srt"))

            if sub_files:
                sub_path = sub_files[0]
                update_status("Parsing subtitle file with timestamps...")
                t_parse_start = time.time()

                with open(sub_path, "r", encoding="utf-8", errors="replace") as f:
                    raw = f.read()

                def ts_to_hms(ts_str: str) -> str:
                    ts_str = ts_str.strip().split()[0]
                    parts = ts_str.replace(',', '.').split('.')
                    hms = parts[0]
                    segments_t = hms.split(':')
                    if len(segments_t) == 2:
                        hms = f"00:{hms}"
                    return hms

                def extract_native_cue_text(cue_raw: str, lang_code: str) -> str:
                    raw_lines = [l.strip() for l in cue_raw.split('\n') if l.strip()]
                    if not raw_lines:
                        return ""
                    if len(raw_lines) == 1:
                        return raw_lines[0]

                    base_l = (lang_code or "").lower().split('-')[0]

                    if base_l in ["zh", "chi", "zho"]:
                        zh_lines = [l for l in raw_lines if re.search(r'[\u4e00-\u9fff]', l)]
                        if zh_lines:
                            return "".join(zh_lines)
                    elif base_l in ["ja", "jpn"]:
                        ja_lines = [l for l in raw_lines if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', l)]
                        if ja_lines:
                            return "".join(ja_lines)
                    elif base_l in ["ko", "kor"]:
                        ko_lines = [l for l in raw_lines if re.search(r'[\uac00-\ud7af]', l)]
                        if ko_lines:
                            return " ".join(ko_lines)
                    elif base_l in ["ru", "uk", "be", "bg", "sr", "mk", "kk", "ky", "tg"]:
                        cyr_lines = [l for l in raw_lines if re.search(r'[\u0400-\u04ff]', l)]
                        if cyr_lines:
                            return " ".join(cyr_lines)
                    elif base_l in ["ar", "fa", "ur", "ps"]:
                        ar_lines = [l for l in raw_lines if re.search(r'[\u0600-\u06ff]', l)]
                        if ar_lines:
                            return " ".join(ar_lines)
                    elif base_l in ["hi", "mr", "ne", "sa"]:
                        hi_lines = [l for l in raw_lines if re.search(r'[\u0900-\u097f]', l)]
                        if hi_lines:
                            return " ".join(hi_lines)
                    elif base_l in ["th"]:
                        th_lines = [l for l in raw_lines if re.search(r'[\u0e00-\u0e7f]', l)]
                        if th_lines:
                            return "".join(th_lines)
                    elif base_l in ["en", "es", "fr", "de", "it", "pt", "nl", "id", "ms", "vi", "tl", "pl", "cs", "sv", "da", "no", "fi", "tr"]:
                        non_latin = r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff\u0600-\u06ff\u0900-\u097f\u0e00-\u0e7f]'
                        latin_lines = [l for l in raw_lines if not re.search(non_latin, l)]
                        if latin_lines:
                            return " ".join(latin_lines)

                    return " ".join(raw_lines)

                cue_pattern = re.compile(
                    r'(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3})[^\n]*\n(.*?)(?=\n\n|\Z)',
                    re.DOTALL
                )

                transcript_segments = []
                seen_texts = set()

                for match_obj in cue_pattern.finditer(raw):
                    start_raw = match_obj.group(1)
                    end_raw = match_obj.group(2)
                    cue_text = match_obj.group(3).strip()
                    cue_text = re.sub(r'<[^>]+>', '', cue_text).strip()
                    cue_text = re.sub(r'^\d+\s*$', '', cue_text, flags=re.MULTILINE).strip()

                    if not cue_text:
                        continue

                    cue_text = extract_native_cue_text(cue_text, subtitle_lang or spoken_lang)
                    if not cue_text:
                        continue

                    if cue_text in seen_texts:
                        continue
                    seen_texts.add(cue_text)

                    start_hms = ts_to_hms(start_raw)
                    end_hms = ts_to_hms(end_raw)

                    transcript_segments.append({
                        "speaker": "Speaker",
                        "start_str": start_hms,
                        "end_str": end_hms,
                        "text": cue_text
                    })

                full_transcript_text = ""
                for seg in transcript_segments:
                    full_transcript_text += f"Speaker ({seg['start_str']} - {seg['end_str']})\n{seg['text']}\n\n"
                full_transcript_text = full_transcript_text.strip()

                os.remove(sub_path)
                t_parse_sec = round(time.time() - t_parse_start, 2)
                t_total_sec = round(time.time() - start_total_time, 1)

                duration_str = transcript_segments[-1]['end_str'] if transcript_segments else "N/A"
                step_timings_str = f"Inspect: {t_meta_sec}s ??Subs DL: {t_sub_sec}s ??Parse: {t_parse_sec}s"

                for m in dynamic_meetings:
                    if m["id"] == meeting_id:
                        m["status"] = "completed"
                        m["title"] = f"YouTube: {filename}"
                        m["participants"] = 1
                        m["duration"] = duration_str
                        m["summary"] = (
                            f"Subtitles extracted in '{subtitle_lang}' "
                            f"({len(transcript_segments)} cues, {len(full_transcript_text)} chars)."
                        )
                        m["full_transcript"] = full_transcript_text
                        m["segments"] = transcript_segments
                        m["sentiment"] = "Neutral"
                        m["tokens_used"] = "0 tokens (CC Subtitles)"
                        m["processing_time"] = f"{t_total_sec}s"
                        m["step_timings"] = step_timings_str
                        break

                print(f"[{meeting_id}] Subtitle extraction complete. {len(transcript_segments)} cues. Total time: {t_total_sec}s")
                return

        # ?€?€ Step 4: No subtitles ??fall back to audio download + Gemini ?€?€?€?€?€?€?€?€?€
        update_status("No subtitles found. Downloading audio for AI transcription...")
        output_template = os.path.join(temp_dir, f"{meeting_id}_audio.%(ext)s")
        t_dl_start = time.time()

        def run_download():
            return subprocess.run(
                ["yt-dlp", "--js-runtimes", "node", "--remote-components", "ejs:github", "-o", output_template, url],
                capture_output=True
            )

        result_dl = await loop.run_in_executor(None, run_download)
        t_dl_sec = round(time.time() - t_dl_start, 1)

        if result_dl.returncode != 0:
            err = result_dl.stderr.decode(errors="replace")
            raise Exception(f"yt-dlp download failed: {err[:300]}")

        downloaded_files = glob.glob(os.path.join(temp_dir, f"{meeting_id}_*"))
        if not downloaded_files:
            raise Exception("No video file found after download.")

        file_path = downloaded_files[0]
        pre_timings = {"Inspect": f"{t_meta_sec}s", "Video DL": f"{t_dl_sec}s"}
        await process_uploaded_file(file_path, meeting_id, filename, pre_timings=pre_timings, start_time=start_total_time)

    except Exception as e:
        import traceback
        traceback.print_exc()
        update_status(f"Error processing YouTube URL: {str(e)}")

@app.post("/youtube", tags=["Meetings"])
async def dispatch_youtube_bot(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing YouTube URL")
        
    import uuid
    meeting_id = f"yt-{uuid.uuid4().hex[:6]}"
    
    dynamic_meetings.insert(0, {
        "id": meeting_id,
        "title": f"Processing YouTube...",
        "status": "live",
        "participants": 1,
        "duration": "0m",
        "summary": "Initializing YouTube extraction...",
        "sentiment": "Processing"
    })
    
    background_tasks.add_task(process_youtube_url, url, meeting_id)
    return {"status": "success", "message": "YouTube bot dispatched"}
