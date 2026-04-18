FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by Reflex
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install --no-cache-dir uv && \
    uv sync --frozen

# Copy application code
COPY . .

# Build Reflex frontend
RUN .venv/bin/reflex build

# Expose port (Railway uses PORT env var by default)
EXPOSE 3000

# Set environment variables
ENV PORT=3000

# Run Reflex in production mode
CMD [".venv/bin/reflex", "run", "--env", "prod"]
