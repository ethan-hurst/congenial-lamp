/**
 * File Synchronization Service
 * Handles bidirectional sync between IndexedDB and backend
 */
import { fileStorage } from './fileStorage';
import { useWebSocket } from '@/hooks/useWebSocket';

interface SyncStatus {
  isSyncing: boolean;
  lastSyncTime: Date | null;
  pendingChanges: number;
  errors: string[];
}

interface FileChange {
  type: 'create' | 'update' | 'delete' | 'move';
  projectId: string;
  path: string;
  content?: string;
  newPath?: string;
  timestamp: Date;
}

class FileSyncService {
  private syncInterval: number = 5000; // 5 seconds
  private syncTimer: NodeJS.Timeout | null = null;
  private changeQueue: FileChange[] = [];
  private isSyncing: boolean = false;
  private listeners: ((status: SyncStatus) => void)[] = [];

  async startSync(projectId: string, token: string) {
    // Initialize file storage
    await fileStorage.initialize();

    // Start periodic sync
    this.syncTimer = setInterval(() => {
      this.syncProject(projectId, token);
    }, this.syncInterval);

    // Do initial sync
    await this.syncProject(projectId, token);
  }

  stopSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }

  async syncProject(projectId: string, token: string) {
    if (this.isSyncing) return;

    this.isSyncing = true;
    this.notifyListeners();

    try {
      // Get local changes
      const localChanges = await fileStorage.getModifiedFiles(projectId);
      
      // Get remote changes
      const remoteChanges = await this.fetchRemoteChanges(projectId, token);
      
      // Resolve conflicts and apply changes
      await this.resolveAndApplyChanges(projectId, localChanges, remoteChanges, token);
      
      // Process queued changes
      await this.processChangeQueue(token);
      
      this.isSyncing = false;
      this.notifyListeners();
    } catch (error) {
      console.error('Sync error:', error);
      this.isSyncing = false;
      this.notifyListeners();
    }
  }

  async createFile(projectId: string, path: string, content: string) {
    // Create locally
    const file = await fileStorage.createFile(projectId, path, content);
    
    // Queue for sync
    this.queueChange({
      type: 'create',
      projectId,
      path,
      content,
      timestamp: new Date(),
    });
    
    return file;
  }

  async updateFile(projectId: string, path: string, content: string) {
    // Update locally
    const file = await fileStorage.updateFile(projectId, path, content);
    
    // Queue for sync
    this.queueChange({
      type: 'update',
      projectId,
      path,
      content,
      timestamp: new Date(),
    });
    
    return file;
  }

  async deleteFile(projectId: string, path: string) {
    // Delete locally
    await fileStorage.deleteFile(projectId, path);
    
    // Queue for sync
    this.queueChange({
      type: 'delete',
      projectId,
      path,
      timestamp: new Date(),
    });
  }

  async moveFile(projectId: string, oldPath: string, newPath: string) {
    // Move locally
    const file = await fileStorage.moveFile(projectId, oldPath, newPath);
    
    // Queue for sync
    this.queueChange({
      type: 'move',
      projectId,
      path: oldPath,
      newPath,
      timestamp: new Date(),
    });
    
    return file;
  }

  async getFileTree(projectId: string) {
    return fileStorage.getFileTree(projectId);
  }

  async readFile(projectId: string, path: string) {
    return fileStorage.readFile(projectId, path);
  }

  onStatusChange(listener: (status: SyncStatus) => void) {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private queueChange(change: FileChange) {
    this.changeQueue.push(change);
    this.notifyListeners();
  }

  private async processChangeQueue(token: string) {
    while (this.changeQueue.length > 0) {
      const change = this.changeQueue.shift()!;
      
      try {
        await this.uploadChange(change, token);
      } catch (error) {
        console.error('Failed to upload change:', error);
        // Re-queue the change
        this.changeQueue.unshift(change);
        throw error;
      }
    }
  }

  private async uploadChange(change: FileChange, token: string) {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/files`;
    
    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };

    switch (change.type) {
      case 'create':
      case 'update':
        await fetch(`${url}/${change.projectId}${change.path}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            content: change.content,
            timestamp: change.timestamp,
          }),
        });
        break;
        
      case 'delete':
        await fetch(`${url}/${change.projectId}${change.path}`, {
          method: 'DELETE',
          headers,
        });
        break;
        
      case 'move':
        await fetch(`${url}/${change.projectId}/move`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            oldPath: change.path,
            newPath: change.newPath,
            timestamp: change.timestamp,
          }),
        });
        break;
    }
  }

  private async fetchRemoteChanges(projectId: string, token: string) {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/files/${projectId}/changes`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch remote changes');
    }
    
    return response.json();
  }

  private async resolveAndApplyChanges(
    projectId: string,
    localChanges: any[],
    remoteChanges: any[],
    token: string
  ) {
    // Simple conflict resolution: last-write-wins based on timestamp
    // In a real implementation, you'd want more sophisticated conflict resolution
    
    for (const remoteChange of remoteChanges) {
      const localFile = await fileStorage.readFile(projectId, remoteChange.path);
      
      if (!localFile || remoteChange.modifiedAt > localFile.modifiedAt) {
        // Apply remote change
        if (remoteChange.isDeleted) {
          await fileStorage.deleteFile(projectId, remoteChange.path);
        } else if (remoteChange.type === 'file') {
          // Fetch file content
          const content = await this.fetchFileContent(
            projectId,
            remoteChange.path,
            token
          );
          
          if (localFile) {
            await fileStorage.updateFile(projectId, remoteChange.path, content);
          } else {
            await fileStorage.createFile(
              projectId,
              remoteChange.path,
              content,
              remoteChange.mimeType
            );
          }
        } else {
          // Directory
          await fileStorage.createDirectory(projectId, remoteChange.path);
        }
        
        // Mark as synced
        await fileStorage.markAsSynced(remoteChange.id);
      }
    }
  }

  private async fetchFileContent(
    projectId: string,
    path: string,
    token: string
  ): Promise<string> {
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/files/${projectId}${path}`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch file content');
    }
    
    return response.text();
  }

  private notifyListeners() {
    const status: SyncStatus = {
      isSyncing: this.isSyncing,
      lastSyncTime: new Date(),
      pendingChanges: this.changeQueue.length,
      errors: [],
    };
    
    this.listeners.forEach(listener => listener(status));
  }
}

// Export singleton instance
export const fileSyncService = new FileSyncService();