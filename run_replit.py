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
        print("Creating virtual environment...")
        result = run_command(f"{sys.executable} -m venv venv_linux")
        if not result or result.returncode != 0:
            print("Failed to create venv, using system Python...")
            return sys.executable

    # Get pip path
    pip_path = venv_path / "bin" / "pip"
    python_path = venv_path / "bin" / "python"

    # Check if venv was created successfully
    if not pip_path.exists() or not python_path.exists():
        print("Virtual environment not properly created, using system Python...")
        return sys.executable

    # Upgrade pip without using --user flag
    print("Upgrading pip...")
    run_command(f"{pip_path} install --upgrade pip", check=False)

    # Install backend dependencies
    backend_path = Path("codeforge/backend")
    req_file = backend_path / "requirements.replit.txt"
    if not req_file.exists():
        req_file = backend_path / "requirements.txt"

    if not req_file.exists():
        print(f"Requirements file not found at {req_file}")
        return str(python_path)

    print("📦 Installing Python dependencies...")
    # Use pip without --user flag inside virtual environment
    result = run_command(f"{pip_path} install -r {req_file}", check=False)
    if result and result.returncode != 0:
        # If it fails, try with --force-reinstall
        print("Retrying with --force-reinstall...")
        result2 = run_command(f"{pip_path} install --force-reinstall -r {req_file}", check=False)
        if result2 and result2.returncode != 0:
            print("Failed to install dependencies, continuing anyway...")

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
        print("Running database initialization...")
        result = run_command(f"cd codeforge/backend && {python_path} src/scripts/init_db.py", check=False)
        if result and result.returncode != 0:
            print("Database initialization failed, but continuing...")
    else:
        print("Database init script not found, skipping...")

def install_frontend_deps():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")

    frontend_path = Path("codeforge/frontend")
    if not frontend_path.exists():
        print("Frontend directory not found, skipping...")
        return False

    if not (frontend_path / "package.json").exists():
        print("package.json not found, skipping frontend setup...")
        return False

    if not (frontend_path / "node_modules").exists():
        print("Installing npm dependencies...")
        result = run_command("npm install", cwd=str(frontend_path), check=False)
        if result and result.returncode != 0:
            print("Failed to install frontend dependencies")
            return False

    return True

def start_services(python_path, frontend_available=True):
    """Start backend and frontend services"""
    print("🚀 Starting services...")

    # Start backend
    backend_path = Path("codeforge/backend")
    if not backend_path.exists():
        print("❌ Backend directory not found!")
        return

    # Check if main.py exists
    main_file = backend_path / "src" / "main.py"
    if not main_file.exists():
        print("❌ Backend main.py not found!")
        return

    backend_cmd = f"cd {backend_path} && {python_path} -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"
    print(f"Starting backend with: {backend_cmd}")

    try:
        backend_proc = subprocess.Popen(backend_cmd, shell=True)
        print("✅ Backend started successfully")

        # Give backend time to start
        time.sleep(5)

        frontend_proc = None
        if frontend_available:
            # Start frontend
            frontend_path = Path("codeforge/frontend")
            if frontend_path.exists() and (frontend_path / "package.json").exists():
                frontend_cmd = f"cd {frontend_path} && npm run dev"
                print(f"Starting frontend with: {frontend_cmd}")

                try:
                    frontend_proc = subprocess.Popen(frontend_cmd, shell=True, env={**os.environ, "PORT": "5000"})
                    print("✅ Frontend started successfully")
                except Exception as e:
                    print(f"⚠️  Frontend failed to start: {e}")
            else:
                print("⚠️  Frontend not available, running backend only")

        repl_slug = os.environ.get('REPL_SLUG', 'codeforge')
        repl_owner = os.environ.get('REPL_OWNER', 'user')

        print("\n✅ CodeForge is starting up!")
        if frontend_proc:
            print(f"🌐 Frontend: https://{repl_slug}.{repl_owner}.repl.co")
        print(f"🔧 Backend API: https://{repl_slug}.{repl_owner}.repl.co/api")
        print(f"📚 API Docs: https://{repl_slug}.{repl_owner}.repl.co/docs")
        print("\n📧 Default Login:")
        print("   Email: admin@codeforge.dev")
        print("   Password: admin123")
        print("   ⚠️  Please change the password after first login!\n")

        try:
            # Wait for processes
            if frontend_proc:
                backend_proc.wait()
                frontend_proc.wait()
            else:
                backend_proc.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            backend_proc.terminate()
            if frontend_proc:
                frontend_proc.terminate()

    except Exception as e:
        print(f"❌ Failed to start services: {e}")
        return

def main():
    """Main entry point"""
    print("🚀 CodeForge Replit Runner")
    print("=" * 50)

    try:
        # Setup steps
        setup_git()
        python_path = setup_python_env()
        setup_backend_env()
        setup_frontend_env()
        init_database(python_path)
        frontend_available = install_frontend_deps()

        # Start services
        start_services(python_path, frontend_available)

    except Exception as e:
        print(f"❌ Critical error during startup: {e}")
        print("Check the console output above for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()