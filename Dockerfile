FROM python:3.11-alpine

WORKDIR /app

# Install build dependencies for Alpine (only needed during build)
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers

# Copy dependency files
COPY pyproject.toml ./

# Install uv and dependencies (skip optional dependencies to reduce size)
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    apk del .build-deps

# Copy application code
COPY . .

# Expose port (Railway uses PORT env var by default)
EXPOSE 3000

# Set environment variables for production
ENV PORT=3000 \
    REFLEX_ENV=prod

# Reflex will build on first startup in production mode
CMD [".venv/bin/reflex", "run", "--env", "prod"]
