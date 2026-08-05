class VoiceActivityDetector:
    def __init__(self, aggressiveness: int = 2):
        self.aggressiveness = aggressiveness
        # Real implementation would use WebRTC VAD or Silero VAD

    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Detects if an audio chunk contains human speech.
        """
        # Mock logic
        return len(audio_chunk) > 1024 

    def process_segment(self, audio_segment: bytes) -> list[bytes]:
        """
        Takes a larger audio segment (e.g. 5 seconds) and strips out silence,
        returning only the chunks containing active voice.
        """
        # Mock: just returning the segment if it's considered speech
        if self.is_speech(audio_segment):
            return [audio_segment]
        return []
