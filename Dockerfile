ARG PYTHON_VERSION=3.9

# ---------------------------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder
WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
COPY src/ ./src/

# Install runtime dependencies via BuildKit pip cache mount.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install .
# ---------------------------------------------------------------------------
# Stage 2: Application Build
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS app
ARG PORT=8080

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /usr/sbin/nologin -M appuser

RUN mkdir -p /tmp && chown appuser:appgroup /tmp

COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
COPY --chown=appuser:appgroup src/ /app/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=${PORT} \
    UVICORN_PORT=${PORT} \
    HOME=/tmp

WORKDIR /app

USER appuser
EXPOSE ${PORT}

# HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request, sys, os; port = os.environ.get('PORT', '8080'); r = urllib.request.urlopen(f'http://localhost:{port}/health', timeout=5); sys.exit(0 if r.status == 200 else 1)"]

ENTRYPOINT ["uvicorn", "main:app"]
CMD ["--host", "0.0.0.0", "--no-access-log"]