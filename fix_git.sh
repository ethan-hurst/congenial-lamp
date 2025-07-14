#!/bin/bash

echo "🔧 Fixing Git Configuration..."

# Set pull strategy to merge (not rebase)
git config pull.rebase false
git config --global pull.rebase false

# Set user info
git config --global user.email "replit@codeforge.dev"
git config --global user.name "Replit User"

# Add safe directories
git config --global --add safe.directory /home/runner/$REPL_SLUG
git config --global --add safe.directory /workspaces/congenial-lamp
git config --global --add safe.directory .
git config --global --add safe.directory '*'

# Set default branch
git config --global init.defaultBranch main

echo "✅ Git configuration fixed!"
echo ""
echo "You can now run: git pull origin main"
echo "Or if you want to keep your local changes: git pull --strategy=ours origin main"
echo "Or if you want to discard local changes: git reset --hard origin/main"