#!/bin/bash
# Start Ollama daemon in the background
ollama serve &
echo "Ollama is starting..."
sleep 5

# Start FastAPI
echo "Starting FastAPI server..."
exec uvicorn backend.api.fastapi:app --host 0.0.0.0 --port ${PORT:-8000}
