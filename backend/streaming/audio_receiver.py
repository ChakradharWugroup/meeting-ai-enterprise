import asyncio
from typing import Callable
from .stream_buffer import AudioStreamBuffer

class AudioReceiver:
    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        self.buffer = AudioStreamBuffer()
        self.full_audio = bytearray()
        self.is_receiving = False
        self._callbacks = []

    def register_callback(self, callback: Callable):
        """Register a callback for when a chunk of audio is ready for processing."""
        self._callbacks.append(callback)

    async def start_receiving(self):
        self.is_receiving = True
        print(f"[{self.meeting_id}] Started receiving audio stream.")
        # In a real implementation, this would open a WebSocket or WebRTC connection
        # to the Teams media stream.

    async def stop_receiving(self):
        self.is_receiving = False
        print(f"[{self.meeting_id}] Stopped receiving audio stream.")

    async def ingest_audio_chunk(self, chunk: bytes, timestamp: float):
        """Called whenever a new chunk of audio arrives from the meeting."""
        if not self.is_receiving:
            return
            
        self.buffer.add_chunk(chunk, timestamp)
        self.full_audio.extend(chunk)
        
        # If we have enough audio for VAD/Processing (e.g. 5 seconds)
        if self.buffer.is_ready_for_processing():
            audio_segment, segment_time = self.buffer.extract_segment()
            for callback in self._callbacks:
                await callback(self.meeting_id, audio_segment, segment_time)
