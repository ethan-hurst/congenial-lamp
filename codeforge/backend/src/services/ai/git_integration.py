"""
Git Integration Service for AI Agents
Provides automated Git operations for AI-generated code
"""
import os
import subprocess
import asyncio
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Exception raised when Git operations fail"""
    pass


class GitIntegration:
    """
    Git integration service for AI agents
    
    Provides automated commit, branch management, and repository operations
    for AI-generated code changes.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.git_dir = self.project_root / ".git"
        
        # Verify this is a Git repository
        if not self.git_dir.exists():
            raise GitError(f"Not a Git repository: {project_root}")
    
    async def create_agent_branch(
        self,
        agent_type: str,
        task_id: str,
        base_branch: str = "main"
    ) -> str:
        """
        Create a new branch for agent work
        
        Args:
            agent_type: Type of agent (feature_builder, bug_fixer, etc.)
            task_id: Unique task identifier
            base_branch: Base branch to create from
            
        Returns:
            Name of the created branch
        """
        
        # Create branch name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"ai/{agent_type}/{task_id[:8]}_{timestamp}"
        
        try:
            # Ensure we're on the base branch and it's up to date
            await self._run_git_command(["checkout", base_branch])
            await self._run_git_command(["pull", "origin", base_branch])
            
            # Create and checkout new branch
            await self._run_git_command(["checkout", "-b", branch_name])
            
            logger.info(f"Created agent branch: {branch_name}")
            return branch_name
            
        except Exception as e:
            raise GitError(f"Failed to create branch {branch_name}: {str(e)}")
    
    async def stage_files(self, file_paths: List[str]) -> bool:
        """
        Stage files for commit
        
        Args:
            file_paths: List of file paths to stage
            
        Returns:
            True if staging was successful
        """
        
        try:
            # Validate file paths are within project
            for file_path in file_paths:
                full_path = self.project_root / file_path
                if not str(full_path).startswith(str(self.project_root)):
                    raise GitError(f"File path outside project: {file_path}")
            
            # Stage each file
            for file_path in file_paths:
                await self._run_git_command(["add", file_path])
            
            logger.info(f"Staged {len(file_paths)} files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stage files: {str(e)}")
            return False
    
    async def create_commit(
        self,
        message: str,
        agent_type: str,
        task_id: str,
        user_email: str = "ai-agent@codeforge.dev",
        user_name: str = "CodeForge AI Agent"
    ) -> str:
        """
        Create a commit with AI agent attribution
        
        Args:
            message: Commit message
            agent_type: Type of agent making the commit
            task_id: Task identifier
            user_email: Email for commit author
            user_name: Name for commit author
            
        Returns:
            Commit hash
        """
        
        try:
            # Set temporary Git config for this commit
            await self._run_git_command(["config", "user.email", user_email])
            await self._run_git_command(["config", "user.name", user_name])
            
            # Create enhanced commit message
            enhanced_message = self._create_commit_message(message, agent_type, task_id)
            
            # Create commit
            result = await self._run_git_command(["commit", "-m", enhanced_message])
            
            # Get commit hash
            commit_hash = await self._get_current_commit_hash()
            
            logger.info(f"Created commit {commit_hash} by {agent_type}")
            return commit_hash
            
        except Exception as e:
            raise GitError(f"Failed to create commit: {str(e)}")
    
    async def create_pull_request_branch(
        self,
        branch_name: str,
        target_branch: str = "main",
        push_to_remote: bool = True
    ) -> Dict[str, str]:
        """
        Prepare branch for pull request
        
        Args:
            branch_name: Branch to prepare
            target_branch: Target branch for PR
            push_to_remote: Whether to push to remote
            
        Returns:
            PR preparation details
        """
        
        try:
            # Switch to the branch
            await self._run_git_command(["checkout", branch_name])
            
            # Rebase onto target branch if needed
            try:
                await self._run_git_command(["rebase", target_branch])
            except Exception:
                # If rebase fails, try merge instead
                logger.warning(f"Rebase failed, merging {target_branch} instead")
                await self._run_git_command(["merge", target_branch])
            
            # Push to remote if requested
            if push_to_remote:
                await self._run_git_command(["push", "-u", "origin", branch_name])
            
            # Get branch info
            commit_hash = await self._get_current_commit_hash()
            commit_count = await self._get_commit_count_since_branch(target_branch)
            
            return {
                "branch_name": branch_name,
                "target_branch": target_branch,
                "commit_hash": commit_hash,
                "commit_count": commit_count,
                "ready_for_pr": True
            }
            
        except Exception as e:
            raise GitError(f"Failed to prepare PR branch: {str(e)}")
    
    async def get_repository_status(self) -> Dict[str, Any]:
        """
        Get current repository status
        
        Returns:
            Repository status information
        """
        
        try:
            # Get current branch
            current_branch = await self._run_git_command(["branch", "--show-current"])
            current_branch = current_branch.strip()
            
            # Get status
            status_output = await self._run_git_command(["status", "--porcelain"])
            
            # Parse status
            modified_files = []
            untracked_files = []
            staged_files = []
            
            for line in status_output.split('\n'):
                if not line.strip():
                    continue
                
                status_code = line[:2]
                file_path = line[3:]
                
                if status_code[0] in ['M', 'A', 'D']:
                    staged_files.append(file_path)
                if status_code[1] in ['M', 'D']:
                    modified_files.append(file_path)
                elif status_code == '??':
                    untracked_files.append(file_path)
            
            # Get last commit info
            last_commit_hash = await self._get_current_commit_hash()
            last_commit_message = await self._run_git_command(["log", "-1", "--pretty=format:%s"])
            
            return {
                "current_branch": current_branch,
                "staged_files": staged_files,
                "modified_files": modified_files,
                "untracked_files": untracked_files,
                "last_commit_hash": last_commit_hash,
                "last_commit_message": last_commit_message.strip(),
                "clean": len(staged_files) == 0 and len(modified_files) == 0 and len(untracked_files) == 0
            }
            
        except Exception as e:
            raise GitError(f"Failed to get repository status: {str(e)}")
    
    async def create_stash(self, message: str = "AI agent stash") -> str:
        """
        Create a stash of current changes
        
        Args:
            message: Stash message
            
        Returns:
            Stash reference
        """
        
        try:
            result = await self._run_git_command(["stash", "push", "-m", message])
            
            # Get stash reference
            stash_list = await self._run_git_command(["stash", "list"])
            if stash_list.strip():
                latest_stash = stash_list.split('\n')[0].split(':')[0]
                return latest_stash
            
            return "stash@{0}"
            
        except Exception as e:
            raise GitError(f"Failed to create stash: {str(e)}")
    
    async def apply_stash(self, stash_ref: str = "stash@{0}") -> bool:
        """
        Apply a stash
        
        Args:
            stash_ref: Stash reference to apply
            
        Returns:
            True if successful
        """
        
        try:
            await self._run_git_command(["stash", "apply", stash_ref])
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply stash {stash_ref}: {str(e)}")
            return False
    
    async def get_diff(
        self,
        base_branch: str = "main",
        file_path: Optional[str] = None
    ) -> str:
        """
        Get diff between current branch and base branch
        
        Args:
            base_branch: Base branch to compare against
            file_path: Optional specific file to diff
            
        Returns:
            Diff output
        """
        
        try:
            cmd = ["diff", base_branch]
            if file_path:
                cmd.append(file_path)
            
            diff_output = await self._run_git_command(cmd)
            return diff_output
            
        except Exception as e:
            raise GitError(f"Failed to get diff: {str(e)}")
    
    async def validate_commit_readiness(self, files_to_commit: List[str]) -> Dict[str, Any]:
        """
        Validate that files are ready for commit
        
        Args:
            files_to_commit: List of files to validate
            
        Returns:
            Validation results
        """
        
        try:
            validation = {
                "ready": True,
                "issues": [],
                "warnings": [],
                "file_count": len(files_to_commit)
            }
            
            # Check if files exist
            for file_path in files_to_commit:
                full_path = self.project_root / file_path
                if not full_path.exists():
                    validation["issues"].append(f"File does not exist: {file_path}")
                    validation["ready"] = False
            
            # Check for large files
            for file_path in files_to_commit:
                full_path = self.project_root / file_path
                if full_path.exists():
                    size_mb = full_path.stat().st_size / (1024 * 1024)
                    if size_mb > 10:  # 10MB limit
                        validation["warnings"].append(f"Large file: {file_path} ({size_mb:.1f}MB)")
            
            # Check for binary files
            for file_path in files_to_commit:
                if await self._is_binary_file(file_path):
                    validation["warnings"].append(f"Binary file: {file_path}")
            
            # Check Git status
            status = await self.get_repository_status()
            if not status["clean"] and len(status["untracked_files"]) > 0:
                untracked_in_commit = [f for f in files_to_commit if f in status["untracked_files"]]
                if untracked_in_commit:
                    validation["warnings"].append(f"Untracked files will be added: {', '.join(untracked_in_commit)}")
            
            return validation
            
        except Exception as e:
            return {
                "ready": False,
                "issues": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "file_count": 0
            }
    
    async def _run_git_command(self, args: List[str]) -> str:
        """
        Run a Git command
        
        Args:
            args: Git command arguments
            
        Returns:
            Command output
        """
        
        cmd = ["git"] + args
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                raise GitError(f"Git command failed: {' '.join(cmd)}\nError: {error_msg}")
            
            return stdout.decode().strip()
            
        except Exception as e:
            if isinstance(e, GitError):
                raise
            raise GitError(f"Failed to run Git command: {' '.join(cmd)}\nError: {str(e)}")
    
    async def _get_current_commit_hash(self) -> str:
        """Get current commit hash"""
        return await self._run_git_command(["rev-parse", "HEAD"])
    
    async def _get_commit_count_since_branch(self, base_branch: str) -> int:
        """Get number of commits since base branch"""
        try:
            output = await self._run_git_command(["rev-list", "--count", f"{base_branch}..HEAD"])
            return int(output.strip())
        except Exception:
            return 0
    
    async def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary"""
        try:
            full_path = self.project_root / file_path
            with open(full_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False
    
    def _create_commit_message(self, message: str, agent_type: str, task_id: str) -> str:
        """Create enhanced commit message with AI attribution"""
        
        lines = [
            message,
            "",
            f"Generated by: {agent_type}",
            f"Task ID: {task_id}",
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "🤖 This commit was generated by CodeForge AI",
            "",
            "Co-authored-by: CodeForge AI <ai@codeforge.dev>"
        ]
        
        return "\n".join(lines)


class AgentGitWorkflow:
    """
    High-level Git workflow for AI agents
    
    Provides complete workflows for agent operations including
    branch creation, committing, and PR preparation.
    """
    
    def __init__(self, project_root: str):
        self.git = GitIntegration(project_root)
        self.project_root = project_root
    
    async def execute_agent_workflow(
        self,
        agent_type: str,
        task_id: str,
        files_created: List[Dict[str, str]],
        commit_message: str,
        auto_pr: bool = False
    ) -> Dict[str, Any]:
        """
        Execute complete Git workflow for agent
        
        Args:
            agent_type: Type of agent
            task_id: Task identifier
            files_created: List of files created by agent
            commit_message: Commit message
            auto_pr: Whether to prepare for PR automatically
            
        Returns:
            Workflow results
        """
        
        workflow_result = {
            "success": False,
            "branch_created": None,
            "commit_hash": None,
            "files_committed": [],
            "pr_ready": False,
            "errors": []
        }
        
        try:
            # Save current state
            original_status = await self.git.get_repository_status()
            original_branch = original_status["current_branch"]
            
            # Create stash if there are uncommitted changes
            stash_ref = None
            if not original_status["clean"]:
                stash_ref = await self.git.create_stash(f"Pre-agent-{task_id} stash")
            
            # Create agent branch
            branch_name = await self.git.create_agent_branch(agent_type, task_id)
            workflow_result["branch_created"] = branch_name
            
            # Write files to filesystem
            written_files = []
            for file_info in files_created:
                file_path = file_info["path"]
                content = file_info["content"]
                
                # Ensure directory exists
                full_path = Path(self.project_root) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                with open(full_path, 'w') as f:
                    f.write(content)
                
                written_files.append(file_path)
            
            # Validate files before committing
            validation = await self.git.validate_commit_readiness(written_files)
            if not validation["ready"]:
                workflow_result["errors"].extend(validation["issues"])
                return workflow_result
            
            # Stage files
            if await self.git.stage_files(written_files):
                workflow_result["files_committed"] = written_files
            
            # Create commit
            commit_hash = await self.git.create_commit(commit_message, agent_type, task_id)
            workflow_result["commit_hash"] = commit_hash
            
            # Prepare for PR if requested
            if auto_pr:
                pr_info = await self.git.create_pull_request_branch(
                    branch_name, 
                    target_branch=original_branch,
                    push_to_remote=False  # Don't push automatically
                )
                workflow_result["pr_ready"] = pr_info["ready_for_pr"]
                workflow_result["pr_info"] = pr_info
            
            workflow_result["success"] = True
            
        except Exception as e:
            workflow_result["errors"].append(str(e))
            logger.error(f"Agent workflow failed: {str(e)}")
            
            # Try to restore original state
            try:
                if workflow_result["branch_created"]:
                    await self.git._run_git_command(["checkout", original_branch])
                    
                if stash_ref:
                    await self.git.apply_stash(stash_ref)
                    
            except Exception as restore_error:
                logger.error(f"Failed to restore original state: {restore_error}")
        
        return workflow_result


# Singleton instance
_git_integration = None

def get_git_integration(project_root: str) -> GitIntegration:
    """Get Git integration instance"""
    global _git_integration
    if _git_integration is None:
        _git_integration = GitIntegration(project_root)
    return _git_integration

def get_agent_git_workflow(project_root: str) -> AgentGitWorkflow:
    """Get agent Git workflow instance"""
    return AgentGitWorkflow(project_root)