FROM ghcr.io/astral-sh/uv:debian-slim AS base
WORKDIR /app
RUN apt-get update \
  && apt-get install -y libopus0 ca-certificates ffmpeg \
  && update-ca-certificates
COPY pyproject.toml uv.lock ./
RUN uv venv && uv sync

FROM base AS runner
WORKDIR /app
COPY . .
CMD ["uv", "run", "--no-dev", "launcher.py"]
