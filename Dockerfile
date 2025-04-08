FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV directly using pip
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./

# Copy the rest of the application
COPY . .

# Create data directory for SQLite database
RUN mkdir -p /data
ENV DATABASE_PATH=/data/auto_slowmode.db

# Sync dependencies using UV
RUN uv sync

# Run the bot using UV
CMD ["uv", "run", "bot.py"]