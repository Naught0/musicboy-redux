ARG TARGET="aarch64-unknown-linux-musl"

FROM clux/muslrust:stable AS chef
WORKDIR /build
USER root
RUN cargo install cargo-chef

FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder
ARG TARGET
WORKDIR /build
COPY --from=planner /build/recipe.json recipe.json
RUN apt-get update && apt-get install -y --no-install-recommends \
  musl-tools \
  ca-certificates \
  tzdata \
  musl-dev \
  pkg-config \
  build-essential \
  wget \
  tar \
  git \
  && rm -rf /var/lib/apt/lists/*

# 2. Add the Musl Target
#    This allows Rust to cross-compile from Debian to Alpine/Musl
RUN rustup target add $TARGET

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
  --host=$TARGET \
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
# COPY . .
# We explicitly target musl. 
# This separates the host (gnu) from the target (musl), fixing the proc-macro error.
# RUN cargo install --locked --path . --target aarch64-unknown-linux-musl --root /usr/local
RUN cargo chef cook --release --target $TARGET --recipe-path recipe.json
COPY . .
RUN cargo install --locked --path . --root . --target $TARGET

FROM scratch AS runtime
ARG TARGET
WORKDIR /app
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /build/bin/musicboy-redux /app

ENTRYPOINT ["/app/musicboy-redux"]
