/**
 * File System Types
 */

export interface FileNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  content?: string;
  children?: FileNode[];
  size?: number;
  modified?: Date;
  permissions?: string;
  isLoading?: boolean;
  isExpanded?: boolean;
  icon?: string;
}

export interface FileOperation {
  type: 'create' | 'update' | 'delete' | 'rename' | 'move';
  path: string;
  newPath?: string;
  content?: string;
  timestamp: Date;
}

export interface FileSystemState {
  root: FileNode;
  selectedFile: FileNode | null;
  expandedPaths: Set<string>;
  operations: FileOperation[];
}