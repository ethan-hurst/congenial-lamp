"""
File Management Service for CodeForge
Handles file operations, storage, and versioning
"""
import os
import hashlib
import mimetypes
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import aiofiles
import shutil
import tempfile

from ..models.project import ProjectFile
from ..database.connection import get_db
from ..config.settings import settings


class FileService:
    """
    File management service for project files
    """
    
    def __init__(self):
        self.storage_base = Path(settings.FILE_STORAGE_PATH) if hasattr(settings, 'FILE_STORAGE_PATH') else Path("/tmp/codeforge_files")
        self.storage_base.mkdir(parents=True, exist_ok=True)
        
        # Maximum file size (10MB by default)
        self.max_file_size = 10 * 1024 * 1024
        
        # Allowed file extensions (empty list means all allowed)
        self.allowed_extensions = []
        
        # Binary file extensions
        self.binary_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.mp4', '.avi', '.mov', '.mp3', '.wav',
            '.zip', '.tar', '.gz', '.rar',
            '.exe', '.dll', '.so', '.dylib',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.pyc', '.pyo', '.class'
        }
    
    def get_project_storage_path(self, project_id: str) -> Path:
        """Get storage path for a project"""
        return self.storage_base / project_id
    
    def get_file_storage_path(self, project_id: str, file_path: str) -> Path:
        """Get full storage path for a file"""
        # Normalize the file path to prevent directory traversal
        file_path = file_path.lstrip('/')
        file_path = os.path.normpath(file_path)
        
        if file_path.startswith('..') or os.path.isabs(file_path):
            raise ValueError("Invalid file path")
        
        return self.get_project_storage_path(project_id) / file_path
    
    async def create_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        user_id: str,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Create a new file"""
        db = get_db()
        
        try:
            # Check if file already exists
            existing = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == file_path
            ).first()
            
            if existing:
                raise FileExistsError(f"File {file_path} already exists")
            
            # Validate file
            await self._validate_file(file_path, content)
            
            # Create directory structure
            storage_path = self.get_file_storage_path(project_id, file_path)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file to storage
            async with aiofiles.open(storage_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            # Calculate hash
            content_hash = hashlib.sha256(content.encode(encoding)).hexdigest()
            
            # Get file info
            file_size = len(content.encode(encoding))
            mimetype, _ = mimetypes.guess_type(file_path)
            is_binary = self._is_binary_file(file_path)
            
            # Create database record
            file_record = ProjectFile(
                id=str(uuid.uuid4()),
                project_id=project_id,
                path=file_path,
                name=os.path.basename(file_path),
                content=content if not is_binary and file_size < 1024 * 1024 else None,  # Store small text files in DB
                content_hash=content_hash,
                size_bytes=file_size,
                mimetype=mimetype,
                encoding=encoding,
                is_binary=is_binary,
                is_directory=False,
                created_by=user_id,
                updated_by=user_id
            )
            
            db.add(file_record)
            db.commit()
            db.refresh(file_record)
            
            return {
                "id": file_record.id,
                "path": file_record.path,
                "name": file_record.name,
                "size": file_record.size_bytes,
                "mimetype": file_record.mimetype,
                "created_at": file_record.created_at.isoformat(),
                "is_binary": file_record.is_binary
            }
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    async def update_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        user_id: str,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """Update an existing file"""
        db = get_db()
        
        try:
            # Get existing file record
            file_record = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == file_path
            ).first()
            
            if not file_record:
                # File doesn't exist, create it
                return await self.create_file(project_id, file_path, content, user_id, encoding)
            
            # Validate file
            await self._validate_file(file_path, content)
            
            # Write file to storage
            storage_path = self.get_file_storage_path(project_id, file_path)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(storage_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            # Calculate new hash
            content_hash = hashlib.sha256(content.encode(encoding)).hexdigest()
            
            # Update database record
            file_record.content = content if not file_record.is_binary and len(content) < 1024 * 1024 else None
            file_record.content_hash = content_hash
            file_record.size_bytes = len(content.encode(encoding))
            file_record.encoding = encoding
            file_record.updated_by = user_id
            file_record.updated_at = datetime.utcnow()
            file_record.version += 1
            
            db.commit()
            db.refresh(file_record)
            
            return {
                "id": file_record.id,
                "path": file_record.path,
                "name": file_record.name,
                "size": file_record.size_bytes,
                "version": file_record.version,
                "updated_at": file_record.updated_at.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    async def get_file(self, project_id: str, file_path: str) -> Dict[str, Any]:
        """Get file content and metadata"""
        db = get_db()
        
        try:
            # Get file record
            file_record = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == file_path
            ).first()
            
            if not file_record:
                raise FileNotFoundError(f"File {file_path} not found")
            
            # If content is stored in database, return it
            if file_record.content is not None:
                content = file_record.content
            else:
                # Read from storage
                storage_path = self.get_file_storage_path(project_id, file_path)
                
                if not storage_path.exists():
                    raise FileNotFoundError(f"File {file_path} not found in storage")
                
                if file_record.is_binary:
                    # For binary files, return metadata only
                    content = None
                else:
                    async with aiofiles.open(storage_path, 'r', encoding=file_record.encoding) as f:
                        content = await f.read()
            
            return {
                "id": file_record.id,
                "path": file_record.path,
                "name": file_record.name,
                "content": content,
                "size": file_record.size_bytes,
                "mimetype": file_record.mimetype,
                "encoding": file_record.encoding,
                "is_binary": file_record.is_binary,
                "is_directory": file_record.is_directory,
                "version": file_record.version,
                "created_at": file_record.created_at.isoformat(),
                "updated_at": file_record.updated_at.isoformat()
            }
            
        finally:
            db.close()
    
    async def delete_file(self, project_id: str, file_path: str, user_id: str) -> bool:
        """Delete a file"""
        db = get_db()
        
        try:
            # Get file record
            file_record = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == file_path
            ).first()
            
            if not file_record:
                return False
            
            # Delete from storage
            storage_path = self.get_file_storage_path(project_id, file_path)
            if storage_path.exists():
                if storage_path.is_file():
                    storage_path.unlink()
                elif storage_path.is_dir():
                    shutil.rmtree(storage_path)
            
            # Delete from database
            db.delete(file_record)
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    async def list_files(self, project_id: str, directory_path: str = "/") -> List[Dict[str, Any]]:
        """List files in a directory"""
        db = get_db()
        
        try:
            # Normalize directory path
            directory_path = directory_path.rstrip('/') or '/'
            
            # Get files from database
            query = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id
            )
            
            # Filter by directory
            if directory_path == '/':
                # Root directory - get files that don't contain '/' or are in immediate subdirectories
                files = []
                all_files = query.all()
                
                for file_record in all_files:
                    path_parts = file_record.path.strip('/').split('/')
                    if len(path_parts) == 1:  # File in root
                        files.append(file_record)
                    elif len(path_parts) > 1:  # Directory in root
                        dir_name = path_parts[0]
                        # Check if we already have this directory
                        if not any(f.path == dir_name and f.is_directory for f in files):
                            # Create virtual directory entry
                            files.append(type('obj', (object,), {
                                'id': f"dir_{dir_name}",
                                'path': dir_name,
                                'name': dir_name,
                                'is_directory': True,
                                'is_binary': False,
                                'size_bytes': 0,
                                'mimetype': None,
                                'created_at': datetime.utcnow(),
                                'updated_at': datetime.utcnow()
                            })())
            else:
                # Specific directory
                prefix = directory_path.lstrip('/') + '/'
                files = query.filter(ProjectFile.path.like(f"{prefix}%")).all()
                
                # Filter to immediate children only
                immediate_files = []
                seen_dirs = set()
                
                for file_record in files:
                    relative_path = file_record.path[len(prefix):]
                    if '/' not in relative_path:
                        # Direct file
                        immediate_files.append(file_record)
                    else:
                        # File in subdirectory
                        subdir = relative_path.split('/')[0]
                        if subdir not in seen_dirs:
                            seen_dirs.add(subdir)
                            # Create virtual directory entry
                            immediate_files.append(type('obj', (object,), {
                                'id': f"dir_{subdir}",
                                'path': f"{prefix}{subdir}",
                                'name': subdir,
                                'is_directory': True,
                                'is_binary': False,
                                'size_bytes': 0,
                                'mimetype': None,
                                'created_at': datetime.utcnow(),
                                'updated_at': datetime.utcnow()
                            })())
                
                files = immediate_files
            
            # Convert to response format
            result = []
            for file_record in files:
                result.append({
                    "id": file_record.id,
                    "path": file_record.path,
                    "name": file_record.name,
                    "is_directory": file_record.is_directory,
                    "is_binary": file_record.is_binary,
                    "size": file_record.size_bytes,
                    "mimetype": file_record.mimetype,
                    "created_at": file_record.created_at.isoformat(),
                    "updated_at": file_record.updated_at.isoformat()
                })
            
            # Sort: directories first, then files, alphabetically
            result.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
            
            return result
            
        finally:
            db.close()
    
    async def create_directory(self, project_id: str, directory_path: str, user_id: str) -> Dict[str, Any]:
        """Create a directory"""
        db = get_db()
        
        try:
            # Check if directory already exists
            existing = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == directory_path,
                ProjectFile.is_directory == True
            ).first()
            
            if existing:
                raise FileExistsError(f"Directory {directory_path} already exists")
            
            # Create storage directory
            storage_path = self.get_file_storage_path(project_id, directory_path)
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Create database record
            dir_record = ProjectFile(
                id=str(uuid.uuid4()),
                project_id=project_id,
                path=directory_path,
                name=os.path.basename(directory_path),
                is_directory=True,
                is_binary=False,
                size_bytes=0,
                created_by=user_id,
                updated_by=user_id
            )
            
            db.add(dir_record)
            db.commit()
            db.refresh(dir_record)
            
            return {
                "id": dir_record.id,
                "path": dir_record.path,
                "name": dir_record.name,
                "is_directory": True,
                "created_at": dir_record.created_at.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    async def rename_file(
        self,
        project_id: str,
        old_path: str,
        new_path: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Rename/move a file"""
        db = get_db()
        
        try:
            # Get file record
            file_record = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == old_path
            ).first()
            
            if not file_record:
                raise FileNotFoundError(f"File {old_path} not found")
            
            # Check if new path already exists
            existing = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.path == new_path
            ).first()
            
            if existing:
                raise FileExistsError(f"File {new_path} already exists")
            
            # Move file in storage
            old_storage_path = self.get_file_storage_path(project_id, old_path)
            new_storage_path = self.get_file_storage_path(project_id, new_path)
            
            if old_storage_path.exists():
                new_storage_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_storage_path), str(new_storage_path))
            
            # Update database record
            file_record.path = new_path
            file_record.name = os.path.basename(new_path)
            file_record.updated_by = user_id
            file_record.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(file_record)
            
            return {
                "id": file_record.id,
                "old_path": old_path,
                "new_path": new_path,
                "name": file_record.name,
                "updated_at": file_record.updated_at.isoformat()
            }
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary based on extension"""
        extension = Path(file_path).suffix.lower()
        return extension in self.binary_extensions
    
    async def _validate_file(self, file_path: str, content: str):
        """Validate file before saving"""
        # Check file size
        content_size = len(content.encode('utf-8'))
        if content_size > self.max_file_size:
            raise ValueError(f"File too large: {content_size} bytes (max: {self.max_file_size})")
        
        # Check file extension if restrictions exist
        if self.allowed_extensions:
            extension = Path(file_path).suffix.lower()
            if extension not in self.allowed_extensions:
                raise ValueError(f"File type not allowed: {extension}")
        
        # Check for dangerous content (basic scan)
        dangerous_patterns = ['<script>', 'javascript:', 'eval(', 'exec(']
        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if pattern in content_lower:
                raise ValueError(f"Potentially dangerous content detected: {pattern}")
    
    async def get_project_size(self, project_id: str) -> Dict[str, Any]:
        """Get total size of project files"""
        db = get_db()
        
        try:
            files = db.query(ProjectFile).filter(
                ProjectFile.project_id == project_id,
                ProjectFile.is_directory == False
            ).all()
            
            total_size = sum(f.size_bytes for f in files)
            file_count = len(files)
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count
            }
            
        finally:
            db.close()