from sqlalchemy.orm import Session
from .models import Transcript
from pgvector.sqlalchemy import Vector

# from sentence_transformers import SentenceTransformer
# embedder = SentenceTransformer('all-MiniLM-L6-v2') # 384 dimensions (Need to update models.py to 384)

def generate_local_embedding(text: str) -> list[float]:
    """
    Generates a vector embedding locally using sentence-transformers.
    """
    # return embedder.encode(text).tolist()
    return [0.0] * 384 # Mock embedding of size 384

def search_similar_transcripts(db: Session, meeting_id: str, query_embedding: list[float], limit: int = 5):
    """
    Searches for transcripts in a specific meeting that are semantically similar 
    to the query embedding using pgvector's L2 distance (<->).
    """
    results = db.query(Transcript).filter(
        Transcript.meeting_id == meeting_id,
        Transcript.embedding != None
    ).order_by(
        Transcript.embedding.l2_distance(query_embedding)
    ).limit(limit).all()
    
    return results

def get_transcript_context(db: Session, meeting_id: str, query_embedding: list[float], limit: int = 5) -> str:
    """
    Helper to get formatted string context from similar transcripts for RAG injection.
    """
    similar_transcripts = search_similar_transcripts(db, meeting_id, query_embedding, limit)
    context_lines = []
    for t in similar_transcripts:
        speaker = t.speaker or "Unknown"
        context_lines.append(f"[{speaker}]: {t.text}")
    return "\n".join(context_lines)
