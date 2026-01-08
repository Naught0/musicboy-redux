# --- Chef Stage: Caches cargo-chef ---
FROM rust:alpine AS chef
WORKDIR /build

# Install build tools.
# We include 'opus-dev' and 'openssl-dev' so pkg-config can find the system libraries.
# We include 'git' in case any dependencies need to be fetched.
RUN apk add --no-cache \
  musl-dev \
  pkgconfig \
  openssl-dev \
  opus-dev \
  cmake \
  build-base \
  git

RUN cargo install cargo-chef

# --- Planner Stage ---
FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

# --- Builder Stage ---
FROM chef AS builder
COPY --from=planner /build/recipe.json recipe.json

# CRITICAL FIX: Force Dynamic Linking
# Rust on Alpine (musl) defaults to static linking ('crt-static').
# We disable this so it links against the shared libraries (.so) provided by apk.
# This prevents the linker errors (cannot find -lopus) and the CMake errors.
ENV RUSTFLAGS="-C target-feature=-crt-static"

# Cook dependencies
RUN cargo chef cook --release --recipe-path recipe.json

COPY . .
# Build the binary
RUN cargo install --locked --path . --root /usr/local

# --- Runtime Stage ---
FROM alpine:latest AS runtime

# Install Runtime Dependencies
# Since we linked dynamically, we MUST install the shared libraries here.
# (libssl3, opus, libgcc)
RUN apk add --no-cache \
  ffmpeg \
  python3 \
  py3-pip \
  nodejs \
  ca-certificates \
  tzdata \
  libssl3 \
  opus \
  libgcc \
  libstdc++

# Install yt-dlp
RUN pip3 install --break-system-packages -U yt-dlp

WORKDIR /app
COPY --from=builder /usr/local/bin/musicboy-redux /usr/local/bin/musicboy-redux

ENV NODE_PATH=/usr/bin/node
ENV RUST_LOG=info

ENTRYPOINT ["/usr/local/bin/musicboy-redux"]
