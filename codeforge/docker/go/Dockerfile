# Go development container for CodeForge
FROM codeforge/base:latest

USER root

# Install Go
ENV GO_VERSION=1.21.5
RUN wget https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz && \
    rm go${GO_VERSION}.linux-amd64.tar.gz

# Set Go environment variables
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/home/codeforge/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Install Go tools
RUN go install golang.org/x/tools/gopls@latest && \
    go install github.com/go-delve/delve/cmd/dlv@latest && \
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest && \
    go install github.com/fatih/gomodifytags@latest && \
    go install github.com/josharian/impl@latest && \
    go install github.com/cweill/gotests/gotests@latest && \
    go install github.com/ramya-rao-a/go-outline@latest && \
    go install github.com/uudashr/gopkgs/v2/cmd/gopkgs@latest && \
    go install honnef.co/go/tools/cmd/staticcheck@latest && \
    go install golang.org/x/tools/cmd/goimports@latest && \
    go install github.com/mgechev/revive@latest && \
    go install github.com/go-swagger/go-swagger/cmd/swagger@latest && \
    go install github.com/swaggo/swag/cmd/swag@latest

# Install additional development tools
RUN go install github.com/air-verse/air@latest && \
    go install github.com/cosmtrek/air@latest

USER codeforge

# Create Go workspace
RUN mkdir -p ~/go/{src,pkg,bin}

# Set up Go environment for user
RUN echo 'export GOPATH=$HOME/go' >> ~/.bashrc && \
    echo 'export PATH=$PATH:/usr/local/go/bin:$GOPATH/bin' >> ~/.bashrc && \
    echo 'export GO111MODULE=on' >> ~/.bashrc

# Pre-download common Go modules
RUN go mod download github.com/gin-gonic/gin@latest && \
    go mod download github.com/gorilla/mux@latest && \
    go mod download github.com/labstack/echo/v4@latest && \
    go mod download gorm.io/gorm@latest && \
    go mod download github.com/stretchr/testify@latest

CMD ["/bin/bash"]