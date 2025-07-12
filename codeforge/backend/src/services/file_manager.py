"""
File Manager Service for CodeForge
Handles file operations, versioning, and collaboration
"""
import os
import asyncio
import aiofiles
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, AsyncIterator
import zipfile
import tarfile
import shutil
from dataclasses import dataclass
import magic
import pygments
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

from ..config.settings import settings
from ..models.project import Project
from ..security.file_security import FileSecurity


@dataclass
class FileMetadata:
    """File metadata information"""
    path: str
    name: str
    size: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    permissions: str
    owner: str
    checksum: str
    is_directory: bool
    is_binary: bool
    
    def to_dict(self) -> Dict:
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "permissions": self.permissions,
            "owner": self.owner,
            "checksum": self.checksum,
            "is_directory": self.is_directory,
            "is_binary": self.is_binary
        }


class FileManager:
    """
    Advanced file management with:
    - Secure file operations
    - Version control integration
    - Real-time collaboration
    - File search and indexing
    - Archive support
    - Syntax highlighting
    """
    
    def __init__(self):
        self.file_security = FileSecurity()
        self.mime = magic.Magic(mime=True)
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
            '.java', '.go', '.rs', '.c', '.cpp', '.h', '.hpp',
            '.css', '.scss', '.html', '.xml', '.json', '.yaml',
            '.yml', '.toml', '.ini', '.conf', '.sh', '.bash',
            '.zsh', '.fish', '.vim', '.sql', '.r', '.m'
        }
        
    def _get_project_path(self, project_id: str) -> Path:
        """Get absolute path for project"""
        return Path(settings.STORAGE_PATH) / "projects" / project_id
        
    async def list_directory(
        self,
        project_id: str,
        path: str = "/",
        show_hidden: bool = False
    ) -> List[FileMetadata]:
        """List files in directory"""
        project_path = self._get_project_path(project_id)
        abs_path = project_path / path.lstrip('/')
        
        # Security check
        if not self.file_security.is_safe_path(abs_path, project_path):
            raise ValueError("Invalid path")
            
        if not abs_path.exists() or not abs_path.is_dir():
            raise FileNotFoundError(f"Directory not found: {path}")
            
        files = []
        
        for item in sorted(abs_path.iterdir()):
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith('.'):
                continue
                
            # Skip .git directory always
            if item.name == '.git':
                continue
                
            metadata = await self._get_file_metadata(item, project_path)
            files.append(metadata)
            
        return files
        
    async def _get_file_metadata(self, path: Path, base_path: Path) -> FileMetadata:
        """Get file metadata"""
        stat = path.stat()
        relative_path = "/" + str(path.relative_to(base_path))
        
        # Determine if binary
        is_binary = False
        checksum = ""
        
        if path.is_file():
            mime_type = self.mime.from_file(str(path))
            is_binary = not mime_type.startswith('text/')
            
            # Calculate checksum for small files
            if stat.st_size < 1024 * 1024:  # 1MB
                async with aiofiles.open(path, 'rb') as f:
                    content = await f.read()
                    checksum = hashlib.sha256(content).hexdigest()
        else:
            mime_type = "inode/directory"
            
        return FileMetadata(
            path=relative_path,
            name=path.name,
            size=stat.st_size,
            mime_type=mime_type,
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc),
            modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            permissions=oct(stat.st_mode)[-3:],
            owner=str(stat.st_uid),
            checksum=checksum,
            is_directory=path.is_dir(),
            is_binary=is_binary
        )
        
    async def read_file(
        self,
        project_id: str,
        file_path: str,
        encoding: str = 'utf-8'
    ) -> Dict:
        """Read file content"""
        project_path = self._get_project_path(project_id)
        abs_path = project_path / file_path.lstrip('/')
        
        # Security check
        if not self.file_security.is_safe_path(abs_path, project_path):
            raise ValueError("Invalid path")
            
        if not abs_path.exists() or not abs_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Check file size
        if abs_path.stat().st_size > self.max_file_size:
            raise ValueError(f"File too large: {file_path}")
            
        # Get metadata
        metadata = await self._get_file_metadata(abs_path, project_path)
        
        # Read content
        if metadata.is_binary:
            # Return base64 encoded for binary files
            async with aiofiles.open(abs_path, 'rb') as f:
                content = await f.read()
                import base64
                content_str = base64.b64encode(content).decode('ascii')
                
            return {
                "content": content_str,
                "encoding": "base64",
                "metadata": metadata.to_dict()
            }
        else:
            # Text file
            try:
                async with aiofiles.open(abs_path, 'r', encoding=encoding) as f:
                    content = await f.read()
                    
                # Syntax highlighting for supported files
                highlighted = None
                if abs_path.suffix in self.text_extensions:
                    try:
                        lexer = get_lexer_for_filename(abs_path.name)
                        formatter = HtmlFormatter(style='monokai', noclasses=True)
                        highlighted = pygments.highlight(content, lexer, formatter)
                    except:
                        pass
                        
                return {
                    "content": content,
                    "encoding": encoding,
                    "metadata": metadata.to_dict(),
                    "highlighted": highlighted
                }
            except UnicodeDecodeError:
                # Fallback to binary
                return await self.read_file(project_id, file_path, 'binary')
                
    async def write_file(
        self,
        project_id: str,
        file_path: str,
        content: str,
        encoding: str = 'utf-8',
        create_dirs: bool = True
    ) -> FileMetadata:
        """Write file content"""
        project_path = self._get_project_path(project_id)
        abs_path = project_path / file_path.lstrip('/')
        
        # Security check
        if not self.file_security.is_safe_path(abs_path, project_path):
            raise ValueError("Invalid path")
            
        # Create parent directories if needed
        if create_dirs:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
        # Write content
        if encoding == 'base64':
            # Binary file
            import base64
            async with aiofiles.open(abs_path, 'wb') as f:
                await f.write(base64.b64decode(content))
        else:
            # Text file
            async with aiofiles.open(abs_path, 'w', encoding=encoding) as f:
                await f.write(content)
                
        # Return metadata
        return await self._get_file_metadata(abs_path, project_path)
        
    async def create_directory(
        self,
        project_id: str,
        dir_path: str
    ) -> FileMetadata:
        """Create directory"""
        project_path = self._get_project_path(project_id)
        abs_path = project_path / dir_path.lstrip('/')
        
        # Security check
        if not self.file_security.is_safe_path(abs_path, project_path):
            raise ValueError("Invalid path")
            
        # Create directory
        abs_path.mkdir(parents=True, exist_ok=True)
        
        return await self._get_file_metadata(abs_path, project_path)
        
    async def delete_path(
        self,
        project_id: str,
        path: str,
        recursive: bool = False
    ) -> bool:
        """Delete file or directory"""
        project_path = self._get_project_path(project_id)
        abs_path = project_path / path.lstrip('/')
        
        # Security check
        if not self.file_security.is_safe_path(abs_path, project_path):
            raise ValueError("Invalid path")
            
        if not abs_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
            
        if abs_path.is_dir():
            if recursive:
                shutil.rmtree(abs_path)
            else:
                abs_path.rmdir()  # Fails if not empty
        else:
            abs_path.unlink()
            
        return True
        
    async def rename_path(
        self,
        project_id: str,
        old_path: str,
        new_path: str
    ) -> FileMetadata:
        """Rename file or directory"""
        project_path = self._get_project_path(project_id)
        old_abs = project_path / old_path.lstrip('/')
        new_abs = project_path / new_path.lstrip('/')
        
        # Security checks
        if not self.file_security.is_safe_path(old_abs, project_path):
            raise ValueError("Invalid old path")
        if not self.file_security.is_safe_path(new_abs, project_path):
            raise ValueError("Invalid new path")
            
        if not old_abs.exists():
            raise FileNotFoundError(f"Path not found: {old_path}")
            
        if new_abs.exists():
            raise FileExistsError(f"Path already exists: {new_path}")
            
        # Rename
        old_abs.rename(new_abs)
        
        return await self._get_file_metadata(new_abs, project_path)
        
    async def copy_path(
        self,
        project_id: str,
        src_path: str,
        dst_path: str
    ) -> FileMetadata:
        """Copy file or directory"""
        project_path = self._get_project_path(project_id)
        src_abs = project_path / src_path.lstrip('/')
        dst_abs = project_path / dst_path.lstrip('/')
        
        # Security checks
        if not self.file_security.is_safe_path(src_abs, project_path):
            raise ValueError("Invalid source path")
        if not self.file_security.is_safe_path(dst_abs, project_path):
            raise ValueError("Invalid destination path")
            
        if not src_abs.exists():
            raise FileNotFoundError(f"Source not found: {src_path}")
            
        if dst_abs.exists():
            raise FileExistsError(f"Destination exists: {dst_path}")
            
        # Copy
        if src_abs.is_dir():
            shutil.copytree(src_abs, dst_abs)
        else:
            shutil.copy2(src_abs, dst_abs)
            
        return await self._get_file_metadata(dst_abs, project_path)
        
    async def search_files(
        self,
        project_id: str,
        query: str,
        path: str = "/",
        file_pattern: Optional[str] = None,
        content_search: bool = False,
        max_results: int = 100
    ) -> List[Dict]:
        """Search for files"""
        project_path = self._get_project_path(project_id)
        search_path = project_path / path.lstrip('/')
        
        # Security check
        if not self.file_security.is_safe_path(search_path, project_path):
            raise ValueError("Invalid path")
            
        results = []
        count = 0
        
        async for file_path in self._walk_directory(search_path):
            if count >= max_results:
                break
                
            relative_path = "/" + str(file_path.relative_to(project_path))
            
            # Check file pattern
            if file_pattern:
                import fnmatch
                if not fnmatch.fnmatch(file_path.name, file_pattern):
                    continue
                    
            # Check filename
            if query.lower() in file_path.name.lower():
                metadata = await self._get_file_metadata(file_path, project_path)
                results.append({
                    "type": "filename",
                    "path": relative_path,
                    "metadata": metadata.to_dict()
                })
                count += 1
                continue
                
            # Content search for text files
            if content_search and file_path.is_file() and file_path.suffix in self.text_extensions:
                if file_path.stat().st_size < 1024 * 1024:  # 1MB limit
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                            if query.lower() in content.lower():
                                # Find line numbers
                                lines = content.splitlines()
                                matches = []
                                for i, line in enumerate(lines):
                                    if query.lower() in line.lower():
                                        matches.append({
                                            "line": i + 1,
                                            "text": line.strip()[:100]
                                        })
                                        
                                metadata = await self._get_file_metadata(file_path, project_path)
                                results.append({
                                    "type": "content",
                                    "path": relative_path,
                                    "metadata": metadata.to_dict(),
                                    "matches": matches[:5]  # First 5 matches
                                })
                                count += 1
                    except:
                        pass
                        
        return results
        
    async def _walk_directory(self, path: Path) -> AsyncIterator[Path]:
        """Recursively walk directory"""
        for item in path.iterdir():
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
                
            if item.is_dir():
                async for sub_item in self._walk_directory(item):
                    yield sub_item
            else:
                yield item
                
    async def create_archive(
        self,
        project_id: str,
        paths: List[str],
        archive_name: str,
        archive_type: str = "zip"
    ) -> str:
        """Create archive from paths"""
        project_path = self._get_project_path(project_id)
        archive_path = project_path / archive_name
        
        # Security check for archive path
        if not self.file_security.is_safe_path(archive_path, project_path):
            raise ValueError("Invalid archive path")
            
        # Validate all source paths
        abs_paths = []
        for path in paths:
            abs_path = project_path / path.lstrip('/')
            if not self.file_security.is_safe_path(abs_path, project_path):
                raise ValueError(f"Invalid path: {path}")
            if not abs_path.exists():
                raise FileNotFoundError(f"Path not found: {path}")
            abs_paths.append(abs_path)
            
        # Create archive
        if archive_type == "zip":
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for abs_path in abs_paths:
                    if abs_path.is_dir():
                        for file_path in abs_path.rglob('*'):
                            if file_path.is_file():
                                arcname = file_path.relative_to(project_path)
                                zf.write(file_path, arcname)
                    else:
                        arcname = abs_path.relative_to(project_path)
                        zf.write(abs_path, arcname)
        elif archive_type in ("tar", "tar.gz", "tgz"):
            mode = 'w:gz' if archive_type in ("tar.gz", "tgz") else 'w'
            with tarfile.open(archive_path, mode) as tf:
                for abs_path in abs_paths:
                    arcname = abs_path.relative_to(project_path)
                    tf.add(abs_path, arcname)
        else:
            raise ValueError(f"Unsupported archive type: {archive_type}")
            
        return "/" + str(archive_path.relative_to(project_path))
        
    async def extract_archive(
        self,
        project_id: str,
        archive_path: str,
        extract_to: str = "/"
    ) -> List[str]:
        """Extract archive"""
        project_path = self._get_project_path(project_id)
        abs_archive = project_path / archive_path.lstrip('/')
        extract_path = project_path / extract_to.lstrip('/')
        
        # Security checks
        if not self.file_security.is_safe_path(abs_archive, project_path):
            raise ValueError("Invalid archive path")
        if not self.file_security.is_safe_path(extract_path, project_path):
            raise ValueError("Invalid extract path")
            
        if not abs_archive.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
            
        extracted_files = []
        
        # Determine archive type
        if abs_archive.suffix == '.zip':
            with zipfile.ZipFile(abs_archive, 'r') as zf:
                for member in zf.namelist():
                    # Security check for extracted paths
                    member_path = extract_path / member
                    if self.file_security.is_safe_path(member_path, project_path):
                        zf.extract(member, extract_path)
                        extracted_files.append("/" + str((extract_path / member).relative_to(project_path)))
        elif abs_archive.suffix in ('.tar', '.gz', '.tgz'):
            mode = 'r:gz' if abs_archive.suffix in ('.gz', '.tgz') else 'r'
            with tarfile.open(abs_archive, mode) as tf:
                for member in tf.getmembers():
                    # Security check for extracted paths
                    member_path = extract_path / member.name
                    if self.file_security.is_safe_path(member_path, project_path):
                        tf.extract(member, extract_path)
                        extracted_files.append("/" + str((extract_path / member.name).relative_to(project_path)))
        else:
            raise ValueError("Unsupported archive format")
            
        return extracted_files