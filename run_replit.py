#!/usr/bin/env python3
"""
CodeForge Replit Runner - Python-based startup script for better compatibility
"""
import os
import sys
import subprocess
import time
import secrets
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return output"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"Error: {result.stderr}")
        return result
    except Exception as e:
        print(f"Command failed: {e}")
        return None

def setup_git():
    """Configure git to avoid errors in Replit"""
    print("🔧 Configuring git...")
    repl_slug = os.environ.get('REPL_SLUG', 'codeforge')
    
    # Configure safe directory
    run_command(f'git config --global --add safe.directory /home/runner/{repl_slug}', check=False)
    run_command(f'git config --global --add safe.directory /workspaces/congenial-lamp', check=False)
    run_command(f'git config --global --add safe.directory .', check=False)
    
    # Configure user
    run_command('git config --global user.email "replit@codeforge.dev"', check=False)
    run_command('git config --global user.name "Replit User"', check=False)
    
    # Configure pull strategy to avoid divergent branches error
    run_command('git config --global pull.rebase false', check=False)
    run_command('git config pull.rebase false', check=False)
    
    # Set default branch name
    run_command('git config --global init.defaultBranch main', check=False)

def setup_python_env():
    """Setup Python virtual environment"""
    print("🐍 Setting up Python environment...")
    
    venv_path = Path("venv_linux")
    if not venv_path.exists():
        run_command(f"{sys.executable} -m venv venv_linux")
    
    # Get pip path
    pip_path = venv_path / "bin" / "pip"
    python_path = venv_path / "bin" / "python"
    
    # Upgrade pip
    run_command(f"{pip_path} install --upgrade pip")
    
    # Install backend dependencies
    backend_path = Path("codeforge/backend")
    req_file = backend_path / "requirements.replit.txt"
    if not req_file.exists():
        req_file = backend_path / "requirements.txt"
    
    print("📦 Installing Python dependencies...")
    run_command(f"{pip_path} install -r {req_file}")
    
    return str(python_path)

def setup_backend_env():
    """Create backend .env file"""
    print("🔐 Setting up backend environment...")
    
    env_path = Path("codeforge/backend/.env")
    if not env_path.exists():
        repl_slug = os.environ.get('REPL_SLUG', 'codeforge')
        repl_owner = os.environ.get('REPL_OWNER', 'user')
        
        env_content = f"""# Database
DATABASE_URL=postgresql://codeforge:codeforge@localhost:5432/codeforge_db
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY={secrets.token_urlsafe(32)}
JWT_SECRET_KEY={secrets.token_urlsafe(32)}

# Application
APP_NAME=CodeForge
ENVIRONMENT=development
DEBUG=True
CORS_ORIGINS=["http://localhost:3000","https://{repl_slug}.{repl_owner}.repl.co","https://*.replit.dev","https://*.repl.co"]

# Frontend URL
FRONTEND_URL=https://{repl_slug}.{repl_owner}.repl.co

# Optional API Keys (add your own)
# OPENAI_API_KEY=your_key_here
# GITHUB_CLIENT_ID=your_client_id
# GITHUB_CLIENT_SECRET=your_client_secret
"""
        env_path.write_text(env_content)

def setup_frontend_env():
    """Create frontend .env file"""
    print("⚛️ Setting up frontend environment...")
    
    env_path = Path("codeforge/frontend/.env")
    if not env_path.exists():
        repl_slug = os.environ.get('REPL_SLUG', 'codeforge')
        repl_owner = os.environ.get('REPL_OWNER', 'user')
        
        env_content = f"""REACT_APP_API_URL=https://{repl_slug}.{repl_owner}.repl.co
REACT_APP_WS_URL=wss://{repl_slug}.{repl_owner}.repl.co
"""
        env_path.write_text(env_content)

def init_database(python_path):
    """Initialize the database"""
    print("🗄️ Initializing database...")
    
    # Simple database setup without requiring PostgreSQL to be running
    init_script = Path("codeforge/backend/src/scripts/init_db.py")
    if init_script.exists():
        run_command(f"{python_path} {init_script}", check=False)
    else:
        print("Database init script not found, skipping...")

def install_frontend_deps():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")
    
    frontend_path = Path("codeforge/frontend")
    if not (frontend_path / "node_modules").exists():
        run_command("npm install", cwd=str(frontend_path))

def start_services(python_path):
    """Start backend and frontend services"""
    print("🚀 Starting services...")
    
    # Start backend
    backend_path = Path("codeforge/backend")
    backend_cmd = f"{python_path} -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"
    backend_proc = subprocess.Popen(backend_cmd, shell=True, cwd=str(backend_path))
    
    # Give backend time to start
    time.sleep(3)
    
    # Start frontend
    frontend_path = Path("codeforge/frontend")
    frontend_cmd = "npm start"
    frontend_proc = subprocess.Popen(frontend_cmd, shell=True, cwd=str(frontend_path), env={**os.environ, "PORT": "3000"})
    
    repl_slug = os.environ.get('REPL_SLUG', 'codeforge')
    repl_owner = os.environ.get('REPL_OWNER', 'user')
    
    print("\n✅ CodeForge is starting up!")
    print(f"🌐 Frontend: https://{repl_slug}.{repl_owner}.repl.co")
    print(f"🔧 Backend API: https://{repl_slug}.{repl_owner}.repl.co/api")
    print(f"📚 API Docs: https://{repl_slug}.{repl_owner}.repl.co/docs")
    print("\n📧 Default Login:")
    print("   Email: admin@codeforge.dev")
    print("   Password: admin123")
    print("   ⚠️  Please change the password after first login!\n")
    
    try:
        # Wait for processes
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()

def main():
    """Main entry point"""
    print("🚀 CodeForge Replit Runner")
    print("=" * 50)
    
    # Setup steps
    setup_git()
    python_path = setup_python_env()
    setup_backend_env()
    setup_frontend_env()
    init_database(python_path)
    install_frontend_deps()
    
    # Start services
    start_services(python_path)

if __name__ == "__main__":
    main()