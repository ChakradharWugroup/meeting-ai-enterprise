class AudioStreamBuffer:
    def __init__(self, processing_interval_ms: int = 5000):
        self.processing_interval_ms = processing_interval_ms
        self.buffer = bytearray()
        self.start_timestamp = None
        self.current_duration_ms = 0

    def add_chunk(self, chunk: bytes, timestamp: float):
        if self.start_timestamp is None:
            self.start_timestamp = timestamp
            
        self.buffer.extend(chunk)
        # In a real app, calculate duration based on sample rate and chunk size
        # Mocking 100ms per chunk for this example
        self.current_duration_ms += 100 

    def is_ready_for_processing(self) -> bool:
        return self.current_duration_ms >= self.processing_interval_ms

    def extract_segment(self):
        """Extracts the current buffer and resets it."""
        segment = bytes(self.buffer)
        segment_time = self.start_timestamp
        
        self.buffer.clear()
        self.start_timestamp = None
        self.current_duration_ms = 0
        
        return segment, segment_time
