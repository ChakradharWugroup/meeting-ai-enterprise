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
    sudo \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face requires the container to run as a non-root user (uid 1000)
RUN useradd -m -u 1000 user && echo "user ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements and install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and grant ownership to the user
COPY --chown=user backend/ ./backend/
COPY --chown=user teams-bot/ ./teams-bot/

# Install Node dependencies for Playwright
RUN cd teams-bot && npm install playwright ws && sudo npx playwright install --with-deps chromium

# Hugging Face Spaces requires exposing port 7860
EXPOSE 7860

# Run the FastAPI server on port 7860
CMD ["uvicorn", "backend.api.fastapi:app", "--host", "0.0.0.0", "--port", "7860"]
