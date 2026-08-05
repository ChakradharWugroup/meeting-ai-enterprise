FROM python:3.10-slim

# We only need the ffmpeg binary, not the C development headers.
# We will upgrade pip to ensure it downloads pre-compiled Linux wheels 
# instead of trying to compile libraries from source.
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ffmpeg \
    libsndfile1 \
    build-essential \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && mkdir -p /app \
    && cd /app \
    && npm init -y \
    && npm install playwright ws \
    && npx playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY backend/ ./backend/
COPY teams-bot/ ./teams-bot/

# Expose the API port (Default 8000, but overridden by Render)
EXPOSE 8000

# Run the FastAPI server using dynamic Render $PORT
CMD sh -c "uvicorn backend.api.fastapi:app --host 0.0.0.0 --port ${PORT:-8000}"
