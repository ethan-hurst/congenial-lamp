FROM golang:1.21-alpine

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    git \
    curl \
    vim \
    nano \
    bash

# Install Go development tools
RUN go install golang.org/x/tools/gopls@latest && \
    go install github.com/go-delve/delve/cmd/dlv@latest && \
    go install golang.org/x/tools/cmd/goimports@latest && \
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# Create non-root user
RUN adduser -D -u 1000 -s /bin/bash codeforge

# Set up workspace
RUN mkdir -p /workspace && chown -R codeforge:codeforge /workspace

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER codeforge

# Set environment variables
ENV GO111MODULE=on
ENV GOPATH=/home/codeforge/go
ENV PATH="${GOPATH}/bin:/usr/local/go/bin:${PATH}"

# Default command
CMD ["/bin/bash"]