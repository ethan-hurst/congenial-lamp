FROM node:20-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    vim \
    nano \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Install global npm packages for development
RUN npm install -g \
    typescript \
    ts-node \
    nodemon \
    eslint \
    prettier \
    @types/node \
    typescript-language-server \
    vscode-langservers-extracted \
    @vscode/debugadapter

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash codeforge

# Set up workspace
RUN mkdir -p /workspace && chown -R codeforge:codeforge /workspace

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER codeforge

# Set environment variables
ENV NODE_ENV=development

# Default command
CMD ["/bin/bash"]