# --- Builder Stage (Debian) ---
# We use Debian (slim) as the host so compiler plugins work normally.
FROM rust:slim AS builder
WORKDIR /app

# 1. Install Build Tools
#    - musl-tools: Provides 'musl-gcc' to compile C code for Alpine
#    - pkg-config: Finds libraries
#    - build-essential: Standard gcc/make
RUN apt-get update && apt-get install -y \
  musl-tools \
  musl-dev \
  pkg-config \
  build-essential \
  wget \
  tar \
  git \
  && rm -rf /var/lib/apt/lists/*

# 2. Add the Musl Target
#    This allows Rust to cross-compile from Debian to Alpine/Musl
RUN rustup target add aarch64-unknown-linux-musl

# 3. Build Static Opus (Targeting Musl)
#    We use CC=musl-gcc to ensure the C library is compatible with Alpine.
RUN cd /tmp && \
  wget https://archive.mozilla.org/pub/opus/opus-1.3.1.tar.gz && \
  tar xzf opus-1.3.1.tar.gz && \
  cd opus-1.3.1 && \
  ./configure \
  --prefix=/usr/local/musl \
  --disable-shared \
  --enable-static \
  --with-pic \
  --host=aarch64-unknown-linux-musl \
  CC=musl-gcc && \
  make -j$(nproc) && \
  make install

# 4. Environment Variables for Linking
#    Point pkg-config to our custom Musl Opus build
ENV PKG_CONFIG_ALL_STATIC=1
ENV PKG_CONFIG_ALLOW_CROSS=1
ENV PKG_CONFIG_PATH=/usr/local/musl/lib/pkgconfig
ENV CC_aarch64_unknown_linux_musl=musl-gcc

# 5. Build the Rust Binary
COPY . .
# We explicitly target musl. 
# This separates the host (gnu) from the target (musl), fixing the proc-macro error.
RUN cargo install --locked --path . --target aarch64-unknown-linux-musl --root /usr/local

# --- Runtime Stage ---
FROM alpine:latest

# Zero dependencies required. 
# The binary is 100% static (bundled with Musl and Opus).
RUN apk add --no-cache ca-certificates

WORKDIR /app
# Note: The binary is in 'bin', not 'sbin' or other paths, because of --root
COPY --from=builder /usr/local/bin/musicboy-redux /usr/local/bin/musicboy-redux

ENV RUST_LOG=info
ENTRYPOINT ["/usr/local/bin/musicboy-redux"]
