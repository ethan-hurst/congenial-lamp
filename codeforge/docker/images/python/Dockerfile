FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    vim \
    nano \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install common Python development tools
RUN pip install --no-cache-dir \
    ipython \
    black \
    pylint \
    pytest \
    requests \
    numpy \
    pandas \
    matplotlib \
    fastapi \
    uvicorn \
    sqlalchemy \
    python-lsp-server[all] \
    debugpy

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash codeforge

# Set up workspace
RUN mkdir -p /workspace && chown -R codeforge:codeforge /workspace

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER codeforge

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/codeforge/.local/bin:${PATH}"

# Default command
CMD ["/bin/bash"]