FROM python:3.10-slim AS uv-provider
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

FROM python:3.10-slim AS system-deps
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y --no-install-recommends \
  libopus0 \
  ca-certificates \
  ffmpeg \
  && update-ca-certificates \
  && apt-get clean \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/* 

FROM system-deps AS builder
COPY --from=uv-provider /bin/uv /bin/uv
WORKDIR /app
# Optimize uv for container builds
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# Copy only lockfiles first to cache this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Stage 4: Final Runner (The actual image)
FROM system-deps AS runner
WORKDIR /app
# Copy ONLY the virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv
# Copy your application code
COPY bot/ /app/bot/
COPY launcher.py .

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

CMD ["python", "launcher.py"]
