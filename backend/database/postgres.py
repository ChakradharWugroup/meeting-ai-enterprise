import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL format: postgresql://user:password@host:port/dbname
# In Docker, the host is 'db' based on the docker-compose.yml
DB_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:password@localhost:5432/meeting_intelligence"
)

# Setup synchronous engine (can be migrated to async later if needed)
engine = create_engine(DB_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes the database schema."""
    # Note: Import models here to ensure they are registered with Base before creating tables
    import backend.database.models
    
    # Ensure pgvector extension is created before tables that use it
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text('CREATE EXTENSION IF NOT EXISTS vector'))
        conn.commit()

    Base.metadata.create_all(bind=engine)
