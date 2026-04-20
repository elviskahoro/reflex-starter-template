FROM python:3.11-alpine

WORKDIR /app

# Runtime + build tooling: bash/curl/unzip for reflex+bun; nodejs for Next.js build;
# caddy serves the exported frontend; libstdc++/libgcc let bun run on musl Alpine.
RUN apk add --no-cache bash curl unzip nodejs npm caddy libstdc++ libgcc

# Build deps for compiling Python wheels (removed after uv sync)
RUN apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    apk del .build-deps

COPY . .

# Pre-build frontend at image build time so runtime only serves static assets.
RUN .venv/bin/reflex init && \
    .venv/bin/reflex export --frontend-only && \
    mkdir -p /srv && \
    unzip -q frontend.zip -d /srv && \
    rm frontend.zip && \
    rm -rf .web

RUN chmod +x /app/entrypoint.sh

# Create .web directory with permissions for runtime state (Reflex backend-only mode needs this)
RUN mkdir -p /app/.web/backend && chmod -R 755 /app/.web

# Create non-root user
RUN addgroup -S appuser && adduser -S appuser -G appuser
RUN chown -R appuser:appuser /app/.web
USER appuser

# Health check for the app
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

ENV REFLEX_ENV=prod \
    PYTHONUNBUFFERED=1

CMD ["/app/entrypoint.sh"]
