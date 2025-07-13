FROM ubuntu:22.04

# Install basic development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    nano \
    htop \
    tmux \
    net-tools \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash codeforge

# Set up workspace
RUN mkdir -p /workspace && chown -R codeforge:codeforge /workspace

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER codeforge

# Default command
CMD ["/bin/bash"]