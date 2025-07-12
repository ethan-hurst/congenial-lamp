# Python development container for CodeForge
FROM codeforge/base:latest

USER root

# Install Python versions
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y \
    python3.9 python3.9-dev python3.9-venv python3.9-distutils \
    python3.10 python3.10-dev python3.10-venv python3.10-distutils \
    python3.11 python3.11-dev python3.11-venv python3.11-distutils \
    python3.12 python3.12-dev python3.12-venv python3.12-distutils \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Install common Python tools
RUN pip3 install --no-cache-dir \
    pipenv \
    virtualenv \
    black \
    flake8 \
    mypy \
    pylint \
    pytest \
    pytest-cov \
    pytest-asyncio \
    ipython \
    jupyter \
    notebook \
    pandas \
    numpy \
    requests \
    httpx \
    fastapi \
    uvicorn \
    django \
    flask \
    sqlalchemy \
    pydantic

# Install Python Language Server
RUN pip3 install --no-cache-dir \
    python-lsp-server[all] \
    pylsp-mypy \
    pylsp-black \
    pyls-isort \
    python-lsp-ruff

# Install debugpy for debugging
RUN pip3 install --no-cache-dir debugpy

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

USER codeforge

# Add poetry to PATH
ENV PATH="/home/codeforge/.local/bin:${PATH}"

# Create common virtual environment locations
RUN mkdir -p ~/envs ~/.cache/pip

# Pre-create common package caches
RUN python -m pip install --user --upgrade pip setuptools wheel

CMD ["/bin/bash"]