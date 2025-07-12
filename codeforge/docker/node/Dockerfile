# Node.js development container for CodeForge
FROM codeforge/base:latest

USER root

# Install Node Version Manager (nvm) dependencies
RUN apt-get update && apt-get install -y \
    dirmngr \
    gpg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js via NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Yarn and pnpm
RUN npm install -g yarn pnpm

# Install common global packages
RUN npm install -g \
    typescript \
    ts-node \
    nodemon \
    pm2 \
    eslint \
    prettier \
    @angular/cli \
    @vue/cli \
    create-react-app \
    create-next-app \
    gatsby-cli \
    @nestjs/cli \
    express-generator \
    npm-check-updates \
    concurrently \
    http-server \
    json-server \
    vercel \
    netlify-cli

# Install TypeScript Language Server
RUN npm install -g \
    typescript-language-server \
    vscode-langservers-extracted \
    @tailwindcss/language-server \
    emmet-ls

# Install node-gyp dependencies for native modules
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

USER codeforge

# Setup nvm for user
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash && \
    echo 'export NVM_DIR="$HOME/.nvm"' >> ~/.bashrc && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> ~/.bashrc && \
    echo '[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"' >> ~/.bashrc

# Pre-create common directories
RUN mkdir -p ~/.npm ~/.yarn ~/.pnpm-store ~/node_modules

# Configure npm
RUN npm config set prefix ~/.npm-global && \
    echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc

CMD ["/bin/bash"]