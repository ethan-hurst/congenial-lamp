## FEATURE:

A web-based integrated development environment (IDE) that replicates core Replit functionality, including:
- Multi-language code editor with syntax highlighting and auto-completion
- Real-time code execution in isolated containers/sandboxes
- File system management with project structure
- Interactive terminal/console output
- Package dependency management
- User authentication and project persistence
- Basic collaboration features (sharing, forking projects)
- Support for multiple programming languages (Python, JavaScript/Node.js, Java, C++, Go, Ruby, etc.)

## EXAMPLES:

### `examples/basic-editor/`
A minimal implementation showing:
- Monaco Editor integration for code editing
- Basic file tree component
- Simple Python/JavaScript execution using WebAssembly or sandboxed iframes

### `examples/docker-backend/`
Backend service example demonstrating:
- Docker container orchestration for code execution
- API endpoints for running code in isolated environments
- WebSocket implementation for real-time output streaming

### `examples/collaborative-editing/`
Real-time collaboration demo featuring:
- Operational Transformation (OT) or CRDT implementation
- WebSocket-based cursor positions and text synchronization
- User presence indicators

### `examples/file-system/`
Virtual file system implementation showing:
- In-memory file storage with IndexedDB persistence
- File CRUD operations
- Import/export functionality

## DOCUMENTATION:

### Code Editor
- Monaco Editor API: https://microsoft.github.io/monaco-editor/api/index.html
- CodeMirror 6 (alternative): https://codemirror.net/docs/

### Code Execution
- Docker Engine API: https://docs.docker.com/engine/api/
- Firecracker MicroVM: https://firecracker-microvm.github.io/
- WebAssembly System Interface (WASI): https://wasi.dev/
- Pyodide (Python in browser): https://pyodide.org/en/stable/

### Real-time Collaboration
- ShareJS/OT.js: https://github.com/share/sharedb
- Yjs CRDT: https://docs.yjs.dev/
- Socket.io: https://socket.io/docs/v4/

### Security
- Container security best practices: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
- Sandboxing untrusted code: https://www.figma.com/blog/how-we-built-the-figma-plugin-system/

### Architecture References
- Replit's architecture blog posts: https://blog.replit.com/
- Judge0 API (code execution): https://judge0.com/

## OTHER CONSIDERATIONS:

### Security Gotchas
- **Container Escape Prevention**: Ensure proper isolation between user code executions. Use gVisor or Firecracker for enhanced security
- **Resource Limits**: Implement strict CPU, memory, and execution time limits to prevent DoS attacks
- **Network Isolation**: Disable or strictly control network access from user code containers
- **File System Quotas**: Implement per-user storage limits and file count restrictions

### Performance Challenges
- **Cold Start Times**: Pre-warm containers or use lightweight runtimes to reduce initial execution delay
- **Scalability**: Design with horizontal scaling in mind - use message queues for code execution requests
- **Editor Performance**: Large files can crash Monaco Editor - implement virtual scrolling or file size limits

### Common AI Assistant Mistakes
- **Forgetting State Management**: AI often creates stateless examples - ensure proper state management for file system, user sessions, and execution history
- **Oversimplifying Execution**: Running code isn't just `eval()` - proper sandboxing, environment setup, and cleanup are critical
- **Missing Error Boundaries**: Gracefully handle container crashes, timeout errors, and malformed code
- **Ignoring Rate Limiting**: Essential for preventing abuse - implement at API, execution, and storage levels

### Technical Debt Prevention
- **Modular Architecture**: Keep code execution, file management, and editor as separate services
- **Language Agnostic Design**: Don't hardcode language-specific logic - use configuration files
- **Monitoring First**: Build in logging, metrics, and tracing from the start
- **Database Schema Versioning**: Plan for migrations early - user data structure will evolve

### User Experience Details
- **Autosave**: Implement with debouncing to prevent data loss
- **Keyboard Shortcuts**: Match common IDE shortcuts (Cmd/Ctrl+S, Cmd/Ctrl+Enter to run)
- **Mobile Considerations**: Responsive design is challenging for IDEs - consider mobile-specific UI
- **Offline Support**: Cache static assets and implement service workers for better performance