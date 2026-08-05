FROM python:3.10-slim

# Install system dependencies for Playwright, ffmpeg, and node
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY teams-bot/ ./teams-bot/

# Install Node dependencies for Playwright
RUN cd teams-bot && rm -rf node_modules && npm install playwright ws && npx playwright install --with-deps chromium

# Expose port (Render automatically assigns $PORT, but we default to 8000)
EXPOSE 8000

# Run the FastAPI server
CMD sh -c "uvicorn backend.api.fastapi:app --host 0.0.0.0 --port ${PORT:-8000}"
