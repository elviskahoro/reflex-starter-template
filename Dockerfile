FROM python:3.11-slim

WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install uv and dependencies (skip optional dependencies to reduce size)
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

# Copy application code
COPY . .

# Expose port (Railway uses PORT env var by default)
EXPOSE 3000

# Set environment variables for production
ENV PORT=3000 \
    REFLEX_ENV=prod

# Reflex will build on first startup in production mode
CMD [".venv/bin/reflex", "run", "--env", "prod"]
