/**
 * IndexedDB File Storage Service
 * Provides local file storage with sync capabilities
 */

interface FileMetadata {
  id: string;
  projectId: string;
  path: string;
  name: string;
  type: 'file' | 'directory';
  content?: string;
  size: number;
  mimeType?: string;
  createdAt: Date;
  modifiedAt: Date;
  syncedAt?: Date;
  version: number;
  isDeleted?: boolean;
}

interface FileSystemNode {
  path: string;
  name: string;
  type: 'file' | 'directory';
  children?: FileSystemNode[];
  metadata?: FileMetadata;
}

class FileStorageService {
  private dbName = 'CodeForgeFileSystem';
  private dbVersion = 1;
  private db: IDBDatabase | null = null;

  async initialize(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => {
        reject(new Error('Failed to open IndexedDB'));
      };

      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Create object stores
        if (!db.objectStoreNames.contains('files')) {
          const fileStore = db.createObjectStore('files', { keyPath: 'id' });
          fileStore.createIndex('projectId', 'projectId', { unique: false });
          fileStore.createIndex('path', 'path', { unique: false });
          fileStore.createIndex('projectPath', ['projectId', 'path'], { unique: true });
          fileStore.createIndex('modifiedAt', 'modifiedAt', { unique: false });
        }

        if (!db.objectStoreNames.contains('fileCache')) {
          const cacheStore = db.createObjectStore('fileCache', { keyPath: 'path' });
          cacheStore.createIndex('projectId', 'projectId', { unique: false });
        }
      };
    });
  }

  async createFile(
    projectId: string,
    path: string,
    content: string = '',
    mimeType?: string
  ): Promise<FileMetadata> {
    if (!this.db) throw new Error('Database not initialized');

    const file: FileMetadata = {
      id: this.generateId(),
      projectId,
      path,
      name: this.getFileName(path),
      type: 'file',
      content,
      size: new Blob([content]).size,
      mimeType: mimeType || this.getMimeType(path),
      createdAt: new Date(),
      modifiedAt: new Date(),
      version: 1,
    };

    const transaction = this.db.transaction(['files'], 'readwrite');
    const store = transaction.objectStore('files');
    
    return new Promise((resolve, reject) => {
      const request = store.add(file);
      
      request.onsuccess = () => {
        resolve(file);
      };
      
      request.onerror = () => {
        reject(new Error('Failed to create file'));
      };
    });
  }

  async createDirectory(projectId: string, path: string): Promise<FileMetadata> {
    if (!this.db) throw new Error('Database not initialized');

    const directory: FileMetadata = {
      id: this.generateId(),
      projectId,
      path,
      name: this.getFileName(path),
      type: 'directory',
      size: 0,
      createdAt: new Date(),
      modifiedAt: new Date(),
      version: 1,
    };

    const transaction = this.db.transaction(['files'], 'readwrite');
    const store = transaction.objectStore('files');
    
    return new Promise((resolve, reject) => {
      const request = store.add(directory);
      
      request.onsuccess = () => {
        resolve(directory);
      };
      
      request.onerror = () => {
        reject(new Error('Failed to create directory'));
      };
    });
  }

  async readFile(projectId: string, path: string): Promise<FileMetadata | null> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction(['files'], 'readonly');
    const store = transaction.objectStore('files');
    const index = store.index('projectPath');
    
    return new Promise((resolve, reject) => {
      const request = index.get([projectId, path]);
      
      request.onsuccess = () => {
        const file = request.result;
        if (file && !file.isDeleted) {
          resolve(file);
        } else {
          resolve(null);
        }
      };
      
      request.onerror = () => {
        reject(new Error('Failed to read file'));
      };
    });
  }

  async updateFile(
    projectId: string,
    path: string,
    content: string
  ): Promise<FileMetadata> {
    if (!this.db) throw new Error('Database not initialized');

    const existingFile = await this.readFile(projectId, path);
    if (!existingFile) {
      throw new Error('File not found');
    }

    const updatedFile: FileMetadata = {
      ...existingFile,
      content,
      size: new Blob([content]).size,
      modifiedAt: new Date(),
      version: existingFile.version + 1,
    };

    const transaction = this.db.transaction(['files'], 'readwrite');
    const store = transaction.objectStore('files');
    
    return new Promise((resolve, reject) => {
      const request = store.put(updatedFile);
      
      request.onsuccess = () => {
        resolve(updatedFile);
      };
      
      request.onerror = () => {
        reject(new Error('Failed to update file'));
      };
    });
  }

  async deleteFile(projectId: string, path: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const file = await this.readFile(projectId, path);
    if (!file) return;

    // Soft delete
    const deletedFile: FileMetadata = {
      ...file,
      isDeleted: true,
      modifiedAt: new Date(),
      version: file.version + 1,
    };

    const transaction = this.db.transaction(['files'], 'readwrite');
    const store = transaction.objectStore('files');
    
    return new Promise((resolve, reject) => {
      const request = store.put(deletedFile);
      
      request.onsuccess = () => {
        resolve();
      };
      
      request.onerror = () => {
        reject(new Error('Failed to delete file'));
      };
    });
  }

  async moveFile(
    projectId: string,
    oldPath: string,
    newPath: string
  ): Promise<FileMetadata> {
    if (!this.db) throw new Error('Database not initialized');

    const file = await this.readFile(projectId, oldPath);
    if (!file) {
      throw new Error('File not found');
    }

    // Mark old file as deleted
    await this.deleteFile(projectId, oldPath);

    // Create new file at new path
    if (file.type === 'file') {
      return this.createFile(projectId, newPath, file.content, file.mimeType);
    } else {
      return this.createDirectory(projectId, newPath);
    }
  }

  async listFiles(projectId: string, directory: string = '/'): Promise<FileMetadata[]> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction(['files'], 'readonly');
    const store = transaction.objectStore('files');
    const index = store.index('projectId');
    
    return new Promise((resolve, reject) => {
      const request = index.getAll(projectId);
      
      request.onsuccess = () => {
        const files = request.result
          .filter(file => !file.isDeleted)
          .filter(file => {
            const fileDir = this.getDirectory(file.path);
            return fileDir === directory;
          });
        resolve(files);
      };
      
      request.onerror = () => {
        reject(new Error('Failed to list files'));
      };
    });
  }

  async getFileTree(projectId: string): Promise<FileSystemNode> {
    if (!this.db) throw new Error('Database not initialized');

    const allFiles = await this.getAllFiles(projectId);
    return this.buildFileTree(allFiles);
  }

  async getAllFiles(projectId: string): Promise<FileMetadata[]> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction(['files'], 'readonly');
    const store = transaction.objectStore('files');
    const index = store.index('projectId');
    
    return new Promise((resolve, reject) => {
      const request = index.getAll(projectId);
      
      request.onsuccess = () => {
        const files = request.result.filter(file => !file.isDeleted);
        resolve(files);
      };
      
      request.onerror = () => {
        reject(new Error('Failed to get all files'));
      };
    });
  }

  async getModifiedFiles(projectId: string, since?: Date): Promise<FileMetadata[]> {
    if (!this.db) throw new Error('Database not initialized');

    const allFiles = await this.getAllFiles(projectId);
    
    if (!since) {
      return allFiles.filter(file => !file.syncedAt || file.modifiedAt > file.syncedAt);
    }
    
    return allFiles.filter(file => file.modifiedAt > since);
  }

  async markAsSynced(fileId: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const transaction = this.db.transaction(['files'], 'readwrite');
    const store = transaction.objectStore('files');
    
    return new Promise((resolve, reject) => {
      const getRequest = store.get(fileId);
      
      getRequest.onsuccess = () => {
        const file = getRequest.result;
        if (file) {
          file.syncedAt = new Date();
          const putRequest = store.put(file);
          
          putRequest.onsuccess = () => {
            resolve();
          };
          
          putRequest.onerror = () => {
            reject(new Error('Failed to mark file as synced'));
          };
        } else {
          resolve();
        }
      };
      
      getRequest.onerror = () => {
        reject(new Error('Failed to get file'));
      };
    });
  }

  async clearProject(projectId: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const files = await this.getAllFiles(projectId);
    const transaction = this.db.transaction(['files'], 'readwrite');
    const store = transaction.objectStore('files');
    
    const promises = files.map(file => {
      return new Promise<void>((resolve, reject) => {
        const request = store.delete(file.id);
        request.onsuccess = () => resolve();
        request.onerror = () => reject(new Error('Failed to delete file'));
      });
    });
    
    await Promise.all(promises);
  }

  // Helper methods
  private generateId(): string {
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getFileName(path: string): string {
    return path.split('/').pop() || '';
  }

  private getDirectory(path: string): string {
    const parts = path.split('/');
    parts.pop();
    return parts.join('/') || '/';
  }

  private getMimeType(path: string): string {
    const extension = path.split('.').pop()?.toLowerCase();
    
    const mimeTypes: Record<string, string> = {
      'js': 'application/javascript',
      'ts': 'application/typescript',
      'jsx': 'application/javascript',
      'tsx': 'application/typescript',
      'json': 'application/json',
      'html': 'text/html',
      'css': 'text/css',
      'py': 'text/x-python',
      'go': 'text/x-go',
      'rs': 'text/x-rust',
      'java': 'text/x-java',
      'cpp': 'text/x-c++',
      'c': 'text/x-c',
      'md': 'text/markdown',
      'txt': 'text/plain',
      'xml': 'application/xml',
      'yaml': 'application/yaml',
      'yml': 'application/yaml',
    };
    
    return mimeTypes[extension || ''] || 'text/plain';
  }

  private buildFileTree(files: FileMetadata[]): FileSystemNode {
    const root: FileSystemNode = {
      path: '/',
      name: 'root',
      type: 'directory',
      children: [],
    };

    // Sort files by path
    files.sort((a, b) => a.path.localeCompare(b.path));

    // Build tree structure
    files.forEach(file => {
      const parts = file.path.split('/').filter(p => p);
      let current = root;

      parts.forEach((part, index) => {
        const isLast = index === parts.length - 1;
        const currentPath = '/' + parts.slice(0, index + 1).join('/');

        if (isLast) {
          // Add file/directory node
          current.children = current.children || [];
          current.children.push({
            path: currentPath,
            name: part,
            type: file.type,
            metadata: file,
            children: file.type === 'directory' ? [] : undefined,
          });
        } else {
          // Find or create directory node
          current.children = current.children || [];
          let dir = current.children.find(child => child.name === part);
          
          if (!dir) {
            dir = {
              path: currentPath,
              name: part,
              type: 'directory',
              children: [],
            };
            current.children.push(dir);
          }
          
          current = dir;
        }
      });
    });

    return root;
  }
}

// Export singleton instance
export const fileStorage = new FileStorageService();