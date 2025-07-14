#!/bin/bash

# CodeForge Replit Startup Script

echo "🚀 Starting CodeForge on Replit..."

# Fix any git issues first
if [ -d ".git" ]; then
    echo "🔧 Configuring git..."
    # Configure safe directories
    git config --global --add safe.directory /home/runner/$REPL_SLUG 2>/dev/null || true
    git config --global --add safe.directory /workspaces/congenial-lamp 2>/dev/null || true
    git config --global --add safe.directory . 2>/dev/null || true
    
    # Configure user
    git config --global user.email "replit@codeforge.dev" 2>/dev/null || true
    git config --global user.name "Replit User" 2>/dev/null || true
    
    # Configure pull strategy - this fixes the divergent branches error
    git config --global pull.rebase false 2>/dev/null || true
    git config pull.rebase false 2>/dev/null || true
    
    # Set default branch
    git config --global init.defaultBranch main 2>/dev/null || true
    
    echo "✅ Git configuration complete"
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies if needed
if ! command_exists psql; then
    echo "📦 Installing PostgreSQL..."
fi

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
if [ ! -d "venv_linux" ]; then
    python3 -m venv venv_linux
fi

source venv_linux/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd codeforge/backend
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment variables
echo "🔐 Setting up environment variables..."
cat > .env << EOL
# Database
DATABASE_URL=postgresql://codeforge:codeforge@localhost:5432/codeforge_db
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# GitHub OAuth (Optional - add your own)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# OpenAI (Optional - add your own)
OPENAI_API_KEY=your_openai_key

# Application
APP_NAME=CodeForge
ENVIRONMENT=development
DEBUG=True
CORS_ORIGINS=["http://localhost:3000","https://*.replit.dev","https://*.repl.co"]

# Frontend URL
FRONTEND_URL=https://$REPL_SLUG.$REPL_OWNER.repl.co:3000
EOL

# Initialize database
echo "🗄️ Setting up database..."
python src/scripts/init_db.py

# Start backend in background
echo "🚀 Starting backend server..."
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Setup frontend
echo "⚛️ Setting up frontend..."
cd ../../codeforge/frontend

# Install frontend dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Create frontend .env
cat > .env << EOL
REACT_APP_API_URL=https://$REPL_SLUG.$REPL_OWNER.repl.co:8000
REACT_APP_WS_URL=wss://$REPL_SLUG.$REPL_OWNER.repl.co:8000
REACT_APP_GITHUB_CLIENT_ID=your_github_client_id
EOL

# Start frontend
echo "🚀 Starting frontend server..."
npm start &
FRONTEND_PID=$!

echo "✅ CodeForge is starting up!"
echo "🌐 Frontend: https://$REPL_SLUG.$REPL_OWNER.repl.co:3000"
echo "🔧 Backend API: https://$REPL_SLUG.$REPL_OWNER.repl.co:8000"
echo "📚 API Docs: https://$REPL_SLUG.$REPL_OWNER.repl.co:8000/docs"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID