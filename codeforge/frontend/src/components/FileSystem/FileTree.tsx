/**
 * File Tree Component - Shows project file structure
 */
import React, { useState, useEffect } from 'react';
import { FileNode } from '../../types/fileSystem';
import { HiFolder, HiFolderOpen, HiDocument } from 'react-icons/hi';
import clsx from 'clsx';

interface FileTreeProps {
  projectId: string;
  onFileSelect: (file: FileNode) => void;
}

export const FileTree: React.FC<FileTreeProps> = ({ projectId, onFileSelect }) => {
  const [fileTree, setFileTree] = useState<FileNode | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock file tree - in production, fetch from API
    const mockTree: FileNode = {
      id: 'root',
      name: 'workspace',
      path: '/',
      type: 'directory',
      children: [
        {
          id: 'src',
          name: 'src',
          path: '/src',
          type: 'directory',
          children: [
            {
              id: 'index',
              name: 'index.js',
              path: '/src/index.js',
              type: 'file',
              content: '// Welcome to CodeForge!\nconsole.log("Hello, World!");',
            },
            {
              id: 'app',
              name: 'App.js',
              path: '/src/App.js',
              type: 'file',
              content: 'function App() {\n  return <div>Hello CodeForge!</div>;\n}',
            },
          ],
        },
        {
          id: 'package',
          name: 'package.json',
          path: '/package.json',
          type: 'file',
          content: '{\n  "name": "my-project",\n  "version": "1.0.0"\n}',
        },
        {
          id: 'readme',
          name: 'README.md',
          path: '/README.md',
          type: 'file',
          content: '# My CodeForge Project\n\nWelcome to your new project!',
        },
      ],
    };

    setTimeout(() => {
      setFileTree(mockTree);
      setLoading(false);
    }, 500);
  }, [projectId]);

  const toggleExpanded = (path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const renderNode = (node: FileNode, level: number = 0): React.ReactNode => {
    const isExpanded = expandedPaths.has(node.path);
    const isDirectory = node.type === 'directory';

    return (
      <div key={node.id}>
        <div
          className={clsx(
            'flex items-center gap-2 px-2 py-1 hover:bg-accent cursor-pointer rounded',
            'select-none'
          )}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
          onClick={() => {
            if (isDirectory) {
              toggleExpanded(node.path);
            } else {
              onFileSelect(node);
            }
          }}
        >
          {isDirectory ? (
            isExpanded ? (
              <HiFolderOpen className="w-4 h-4 text-blue-500" />
            ) : (
              <HiFolder className="w-4 h-4 text-blue-500" />
            )
          ) : (
            <HiDocument className="w-4 h-4 text-gray-500" />
          )}
          <span className="text-sm">{node.name}</span>
        </div>
        {isDirectory && isExpanded && node.children && (
          <div>
            {node.children.map((child) => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="text-sm text-muted-foreground">Loading files...</div>
      </div>
    );
  }

  if (!fileTree) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="text-sm text-muted-foreground">No files found</div>
      </div>
    );
  }

  return (
    <div className="py-2">
      {fileTree.children?.map((child) => renderNode(child))}
    </div>
  );
};