FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV using the official installation method
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY pyproject.toml uv.lock ./

# Copy the rest of the application
COPY . .

# Create data directory for SQLite database
RUN mkdir -p /data
ENV DATABASE_PATH=/data/auto_slowmode.db

# Sync dependencies using UV
RUN /root/.cargo/bin/uv sync

# Run the bot using UV
CMD ["/root/.cargo/bin/uv", "run", "bot.py"]