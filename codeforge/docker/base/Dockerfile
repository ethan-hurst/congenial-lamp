# Base image for all CodeForge containers
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    build-essential \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    locales \
    sudo \
    openssh-client \
    unzip \
    zip \
    jq \
    tree \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 codeforge && \
    echo "codeforge ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Create workspace directory
RUN mkdir -p /workspace && \
    chown -R codeforge:codeforge /workspace

# Install development tools
RUN apt-get update && apt-get install -y \
    ripgrep \
    fd-find \
    bat \
    fzf \
    ncdu \
    httpie \
    postgresql-client \
    mysql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI for Docker-in-Docker support
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get update && apt-get install -y docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Set up user environment
USER codeforge
WORKDIR /workspace

# Configure git
RUN git config --global user.name "CodeForge User" && \
    git config --global user.email "user@codeforge.dev" && \
    git config --global init.defaultBranch main

# Set up shell
RUN echo 'export PS1="\[\033[01;32m\]codeforge\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]$ "' >> ~/.bashrc && \
    echo 'alias ll="ls -alF"' >> ~/.bashrc && \
    echo 'alias la="ls -A"' >> ~/.bashrc && \
    echo 'alias l="ls -CF"' >> ~/.bashrc

# Entry point
CMD ["/bin/bash"]