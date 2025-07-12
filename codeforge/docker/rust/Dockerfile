# Rust development container for CodeForge
FROM codeforge/base:latest

USER root

# Install Rust dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

USER codeforge

# Install Rust via rustup
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

# Add Rust to PATH
ENV PATH="/home/codeforge/.cargo/bin:${PATH}"

# Install additional Rust toolchains
RUN rustup toolchain install nightly beta && \
    rustup component add rustfmt clippy rust-src rust-analyzer

# Install common Rust tools
RUN cargo install \
    cargo-watch \
    cargo-edit \
    cargo-outdated \
    cargo-audit \
    cargo-tarpaulin \
    cargo-expand \
    cargo-generate \
    mdbook \
    diesel_cli \
    sea-orm-cli \
    sqlx-cli \
    wasm-pack \
    trunk \
    just \
    bacon

# Install sccache for faster builds
RUN cargo install sccache && \
    echo 'export RUSTC_WRAPPER=sccache' >> ~/.bashrc

# Pre-download common crates
RUN cargo install lazy_static && \
    cargo search tokio serde actix-web rocket warp axum diesel sqlx clap

# Configure cargo
RUN mkdir -p ~/.cargo && \
    echo '[build]' > ~/.cargo/config.toml && \
    echo 'target-dir = "/tmp/cargo-target"' >> ~/.cargo/config.toml && \
    echo '' >> ~/.cargo/config.toml && \
    echo '[net]' >> ~/.cargo/config.toml && \
    echo 'git-fetch-with-cli = true' >> ~/.cargo/config.toml

CMD ["/bin/bash"]