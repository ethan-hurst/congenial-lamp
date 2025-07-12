# Web-Based IDE (Replit Clone) - Production-Ready Implementation

**name**: "Web-Based IDE (Replit Clone) - Production-Ready Implementation"  
**description**: Complete production-ready implementation with comprehensive context

## Purpose
A comprehensive Product Requirements Prompt for implementing a full-featured web-based IDE that replicates core Replit functionality with modern security, scalability, and collaboration features. This PRP provides complete context for AI implementation with validation loops.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build a production-ready web-based integrated development environment (IDE) that replicates core Replit functionality including:
- Multi-language Monaco Editor with syntax highlighting and auto-completion
- Secure real-time code execution in isolated containers using gVisor/Docker
- Interactive terminal/console with WebSocket streaming
- Virtual file system with IndexedDB persistence
- User authentication and project management
- Real-time collaboration using CRDT (Yjs)
- Support for Python, JavaScript/Node.js, Java, C++, Go, Ruby
- Package dependency management and project sharing

## Why
- **Business value**: Democratizes coding access through browser-based development
- **Integration**: Modern web IDE competing with CodeSandbox, Replit, and GitHub Codespaces
- **Problems solved**: Eliminates local development setup, enables instant coding, supports remote collaboration

## What
A comprehensive web IDE platform where users can:
- Create, edit, and execute code in multiple languages through a browser
- Collaborate in real-time with other developers
- Manage files and directories in a virtual file system
- Install and manage packages/dependencies
- Share and fork projects publicly or privately
- Access an interactive terminal for command-line operations

### Success Criteria
- [ ] Monaco Editor integrated with syntax highlighting for 7+ languages
- [ ] Secure code execution with <5s cold start times using gVisor containers
- [ ] Real-time collaboration with <100ms latency using Yjs CRDT
- [ ] File system operations with IndexedDB persistence
- [ ] WebSocket terminal with streaming output
- [ ] User authentication and project persistence
- [ ] Package management for Python (pip), Node.js (npm), Java (Maven)
- [ ] Project sharing and forking functionality
- [ ] Security hardening preventing container escapes
- [ ] Performance: 100+ concurrent users per server instance

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://microsoft.github.io/monaco-editor/api/index.html
  why: Core Monaco Editor API, integration patterns, performance optimization
  
- url: https://docs.docker.com/engine/api/
  why: Docker Engine API for container management, resource limits, networking
  
- url: https://docs.yjs.dev/
  why: CRDT-based real-time collaboration, Monaco integration, awareness protocol
  
- url: https://socket.io/docs/v4/
  why: WebSocket communication patterns, real-time features, connection management
  
- url: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
  why: Container security best practices, preventing escape vulnerabilities
  
- url: https://firecracker-microvm.github.io/
  why: Alternative to gVisor for stronger isolation, microVM architecture
  
- url: https://pyodide.org/en/stable/
  why: Python in browser execution, WebAssembly sandboxing alternative
  
- url: https://github.com/microsoft/monaco-editor
  why: Monaco Editor source code, examples, and integration patterns
  
- url: https://github.com/yjs/yjs
  why: Yjs CRDT implementation, Monaco bindings, collaboration examples
  
- url: https://github.com/share/sharedb
  why: Alternative OT-based collaboration (ShareJS) for comparison
  
- url: https://blog.replit.com/
  why: Replit's architecture insights, performance optimization, security approaches
  
- url: https://judge0.com/
  why: Code execution API patterns, language support, security considerations
```

### Current Codebase tree
```bash
.
├── CLAUDE.md                 # Project rules and conventions
├── INITIAL.md               # Feature specification
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md     # PRP template
│   └── EXAMPLE_multi_agent_prp.md
├── README.md               # Context Engineering template docs
└── examples/               # Empty - no existing patterns
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
.
├── frontend/
│   ├── public/
│   │   ├── index.html           # Main application entry point
│   │   └── favicon.ico          # Application icon
│   ├── src/
│   │   ├── components/
│   │   │   ├── Editor/
│   │   │   │   ├── MonacoEditor.tsx    # Monaco Editor wrapper component
│   │   │   │   ├── FileTree.tsx        # File system tree navigation
│   │   │   │   ├── TabBar.tsx          # Open file tabs management
│   │   │   │   └── CollabCursors.tsx   # Real-time cursor rendering
│   │   │   ├── Terminal/
│   │   │   │   ├── XtermTerminal.tsx   # Xterm.js terminal component
│   │   │   │   └── TerminalManager.tsx # Terminal session management
│   │   │   ├── FileSystem/
│   │   │   │   ├── FileExplorer.tsx    # File browser UI
│   │   │   │   ├── FileUpload.tsx      # File upload interface
│   │   │   │   └── FileContextMenu.tsx # Right-click context menu
│   │   │   ├── Collaboration/
│   │   │   │   ├── UserPresence.tsx    # Show active collaborators
│   │   │   │   ├── ShareDialog.tsx     # Project sharing interface
│   │   │   │   └── CommentSystem.tsx   # Code commenting system
│   │   │   ├── Output/
│   │   │   │   ├── ConsoleOutput.tsx   # Code execution output
│   │   │   │   └── ErrorDisplay.tsx    # Error highlighting and display
│   │   │   └── Common/
│   │   │       ├── Layout.tsx          # Main application layout
│   │   │       ├── LoadingSpinner.tsx  # Loading states
│   │   │       └── ErrorBoundary.tsx   # Error handling wrapper
│   │   ├── services/
│   │   │   ├── api.ts                  # HTTP API client
│   │   │   ├── websocket.ts            # WebSocket connection manager
│   │   │   ├── collaboration.ts        # Yjs CRDT integration
│   │   │   ├── fileSystem.ts           # IndexedDB file operations
│   │   │   ├── codeExecution.ts        # Code execution API
│   │   │   └── authentication.ts       # Auth service
│   │   ├── stores/
│   │   │   ├── useEditorStore.ts       # Editor state management
│   │   │   ├── useFileStore.ts         # File system state
│   │   │   ├── useUserStore.ts         # User authentication state
│   │   │   └── useProjectStore.ts      # Project management state
│   │   ├── utils/
│   │   │   ├── languageUtils.ts        # Language detection and config
│   │   │   ├── fileUtils.ts            # File manipulation utilities
│   │   │   └── securityUtils.ts        # Input sanitization
│   │   ├── types/
│   │   │   ├── editor.ts               # Editor-related types
│   │   │   ├── fileSystem.ts           # File system types
│   │   │   └── collaboration.ts        # Collaboration types
│   │   ├── hooks/
│   │   │   ├── useMonaco.ts            # Monaco Editor integration
│   │   │   ├── useWebSocket.ts         # WebSocket connection hook
│   │   │   ├── useFileSystem.ts        # File operations hook
│   │   │   └── useCollaboration.ts     # Real-time collaboration hook
│   │   ├── App.tsx                     # Main React application
│   │   └── main.tsx                    # Application entry point
│   ├── package.json                    # Frontend dependencies
│   ├── vite.config.ts                 # Vite build configuration
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   └── tsconfig.json                  # TypeScript configuration
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py             # Authentication endpoints
│   │   │   │   ├── projects.py         # Project CRUD operations
│   │   │   │   ├── files.py            # File system operations
│   │   │   │   ├── execution.py        # Code execution endpoints
│   │   │   │   └── collaboration.py    # Real-time collaboration
│   │   │   ├── middleware/
│   │   │   │   ├── auth.py             # JWT authentication middleware
│   │   │   │   ├── rate_limit.py       # Rate limiting middleware
│   │   │   │   └── cors.py             # CORS configuration
│   │   │   └── __init__.py             # API package initialization
│   │   ├── services/
│   │   │   ├── container_service.py    # Docker container management
│   │   │   ├── execution_service.py    # Code execution orchestration
│   │   │   ├── file_service.py         # File system operations
│   │   │   ├── collaboration_service.py # Real-time collaboration
│   │   │   ├── auth_service.py         # Authentication logic
│   │   │   └── project_service.py      # Project management
│   │   ├── models/
│   │   │   ├── user.py                 # User data models
│   │   │   ├── project.py              # Project data models
│   │   │   ├── file.py                 # File system models
│   │   │   ├── execution.py            # Execution result models
│   │   │   └── collaboration.py        # Collaboration models
│   │   ├── websocket/
│   │   │   ├── handlers/
│   │   │   │   ├── terminal.py         # Terminal WebSocket handler
│   │   │   │   ├── collaboration.py    # Real-time collaboration
│   │   │   │   └── execution.py        # Live execution output
│   │   │   ├── manager.py              # WebSocket connection manager
│   │   │   └── __init__.py             # WebSocket package init
│   │   ├── security/
│   │   │   ├── container_security.py   # Container security configuration
│   │   │   ├── input_validation.py     # Input sanitization
│   │   │   └── sandbox_manager.py      # Sandbox lifecycle management
│   │   ├── config/
│   │   │   ├── settings.py             # Application configuration
│   │   │   ├── database.py             # Database connection
│   │   │   └── containers.py           # Container configuration
│   │   ├── utils/
│   │   │   ├── language_configs.py     # Language-specific configurations
│   │   │   ├── file_utils.py           # File manipulation utilities
│   │   │   └── monitoring.py           # Logging and metrics
│   │   └── main.py                     # FastAPI application entry
│   ├── containers/
│   │   ├── python/
│   │   │   ├── Dockerfile              # Python execution environment
│   │   │   └── requirements.txt        # Python base packages
│   │   ├── nodejs/
│   │   │   ├── Dockerfile              # Node.js execution environment
│   │   │   └── package.json            # Node.js base packages
│   │   ├── java/
│   │   │   └── Dockerfile              # Java execution environment
│   │   ├── cpp/
│   │   │   └── Dockerfile              # C++ execution environment
│   │   ├── go/
│   │   │   └── Dockerfile              # Go execution environment
│   │   └── ruby/
│   │       └── Dockerfile              # Ruby execution environment
│   ├── requirements.txt                # Python dependencies
│   ├── pyproject.toml                  # Python project configuration
│   └── Dockerfile                      # Backend container image
├── infrastructure/
│   ├── docker-compose.yml              # Local development environment
│   ├── docker-compose.prod.yml         # Production configuration
│   ├── nginx.conf                      # Reverse proxy configuration
│   ├── k8s/
│   │   ├── namespace.yaml              # Kubernetes namespace
│   │   ├── backend-deployment.yaml     # Backend service deployment
│   │   ├── frontend-deployment.yaml    # Frontend service deployment
│   │   ├── redis-deployment.yaml       # Redis for collaboration
│   │   ├── postgres-deployment.yaml    # Database deployment
│   │   ├── ingress.yaml                # Load balancer configuration
│   │   └── network-policy.yaml         # Network security policies
│   └── monitoring/
│       ├── prometheus.yml              # Metrics collection
│       └── grafana-dashboard.json      # Performance monitoring
├── tests/
│   ├── frontend/
│   │   ├── components/                 # Component unit tests
│   │   ├── services/                   # Service integration tests
│   │   └── e2e/                        # End-to-end tests
│   ├── backend/
│   │   ├── unit/                       # Unit tests for services
│   │   ├── integration/                # API integration tests
│   │   └── security/                   # Security penetration tests
│   └── load/
│       └── performance_tests.py        # Load testing scripts
├── docs/
│   ├── API.md                          # API documentation
│   ├── DEPLOYMENT.md                   # Deployment guide
│   ├── SECURITY.md                     # Security implementation details
│   └── ARCHITECTURE.md                 # System architecture overview
├── .env.example                        # Environment variables template
├── .gitignore                          # Git ignore patterns
├── README.md                           # Project documentation
└── Makefile                            # Build and deployment commands
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Monaco Editor requires proper WebAssembly support
# CRITICAL: Yjs requires WebSocket or WebRTC provider for real-time sync
# CRITICAL: Docker containers must run with gVisor for security isolation
# CRITICAL: WebSocket connections need proper reconnection logic
# CRITICAL: File uploads need size limits and virus scanning
# CRITICAL: Container resource limits essential to prevent DoS
# CRITICAL: Always sanitize user code input before execution
# CRITICAL: Use IndexedDB with size quotas for file persistence
# CRITICAL: Monaco workers need proper CORS configuration
# CRITICAL: Container networking must be completely isolated
# CRITICAL: JWT tokens need refresh mechanism for long sessions
# CRITICAL: File system operations need atomic transactions
# CRITICAL: Package installation needs timeout and size limits
# CRITICAL: Terminal sessions need cleanup on disconnect
# CRITICAL: Collaboration awareness needs debouncing for performance
```

## Implementation Blueprint

### Data models and structure

Create the core data models ensuring type safety and consistency across the application.

```python
# Backend Pydantic models for API consistency
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUBY = "ruby"

class FileType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"

class User(BaseModel):
    id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    created_at: datetime
    last_active: datetime

class Project(BaseModel):
    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    owner_id: str
    language: Language
    is_public: bool = Field(default=False)
    fork_count: int = Field(default=0)
    created_at: datetime
    updated_at: datetime
    
class FileSystemItem(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=255)
    path: str = Field(..., description="Full file path")
    type: FileType
    content: Optional[str] = Field(None, description="File content for files")
    size: int = Field(default=0, ge=0)
    parent_id: Optional[str] = None
    project_id: str
    created_at: datetime
    updated_at: datetime
    
class ExecutionRequest(BaseModel):
    code: str = Field(..., max_length=1000000, description="Code to execute")
    language: Language
    stdin: Optional[str] = Field(None, max_length=100000)
    timeout: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds")
    
class ExecutionResult(BaseModel):
    id: str
    status: ExecutionStatus
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exit_code: Optional[int] = None
    execution_time: float = Field(ge=0.0)
    memory_usage: int = Field(ge=0)
    started_at: datetime
    completed_at: Optional[datetime] = None
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Setup Development Environment and Core Infrastructure
CREATE backend/src/config/settings.py:
  - PATTERN: Use pydantic-settings for environment configuration
  - Load database connection, Redis, Docker settings
  - Validate required environment variables on startup
  
CREATE backend/src/main.py:
  - PATTERN: FastAPI application with CORS, authentication, WebSocket support
  - Include all route modules and middleware
  - Setup graceful shutdown for container cleanup
  
CREATE frontend/vite.config.ts:
  - PATTERN: Vite configuration with TypeScript, React, WebSocket proxy
  - Configure Monaco Editor workers and WebAssembly support
  - Setup development server with proper CORS headers

Task 2: Implement Monaco Editor Core
CREATE frontend/src/components/Editor/MonacoEditor.tsx:
  - PATTERN: React component wrapping Monaco with TypeScript support
  - Configure language support, themes, and auto-completion
  - Implement proper disposal and memory management
  
CREATE frontend/src/hooks/useMonaco.ts:
  - PATTERN: Custom hook for Monaco initialization and configuration
  - Handle worker loading, language registration, and theme switching
  - Implement error handling for Monaco loading failures

Task 3: Implement Secure Container Execution Backend
CREATE backend/src/services/container_service.py:
  - PATTERN: Async container management with Docker API
  - Use gVisor runtime for security isolation
  - Implement resource limits, networking isolation, and cleanup
  
CREATE backend/src/security/container_security.py:
  - PATTERN: Security hardening configuration
  - Disable network access, limit syscalls, read-only filesystem
  - Implement container lifecycle monitoring and auto-cleanup

Task 4: Implement File System with IndexedDB
CREATE frontend/src/services/fileSystem.ts:
  - PATTERN: IndexedDB wrapper with async/await interface
  - Implement CRUD operations with atomic transactions
  - Add file size quotas and error handling
  
CREATE frontend/src/components/FileSystem/FileExplorer.tsx:
  - PATTERN: Tree view component for file navigation
  - Support drag-and-drop, context menus, and file operations
  - Implement virtual scrolling for large directory listings

Task 5: Implement Real-Time Collaboration with Yjs
CREATE frontend/src/services/collaboration.ts:
  - PATTERN: Yjs CRDT integration with Monaco Editor
  - Setup WebSocket provider for real-time synchronization
  - Implement awareness protocol for cursors and presence
  
CREATE frontend/src/components/Collaboration/UserPresence.tsx:
  - PATTERN: Real-time user presence indicators
  - Show active collaborators with avatars and cursor positions
  - Implement follow mode and viewport synchronization

Task 6: Implement WebSocket Terminal with Xterm.js
CREATE frontend/src/components/Terminal/XtermTerminal.tsx:
  - PATTERN: Xterm.js integration with WebSocket communication
  - Support command execution, output streaming, and input handling
  - Implement terminal themes and font size adjustment
  
CREATE backend/src/websocket/handlers/terminal.py:
  - PATTERN: WebSocket handler for terminal communication
  - Execute commands in containers with streaming output
  - Implement session management and cleanup

Task 7: Implement Authentication and Project Management
CREATE backend/src/services/auth_service.py:
  - PATTERN: JWT-based authentication with refresh tokens
  - Implement password hashing, token validation, and rate limiting
  - Support OAuth integration for GitHub/Google login
  
CREATE backend/src/api/routes/projects.py:
  - PATTERN: FastAPI routes for project CRUD operations
  - Support project sharing, forking, and permission management
  - Implement project templates and language detection

Task 8: Add Package Management Support
CREATE backend/src/services/package_service.py:
  - PATTERN: Language-specific package installation
  - Support pip (Python), npm (Node.js), Maven (Java) with security
  - Implement timeout limits and sandbox execution
  
CREATE frontend/src/components/Packages/PackageManager.tsx:
  - PATTERN: UI for package search, installation, and management
  - Display package information and dependency trees
  - Implement installation progress tracking

Task 9: Add Code Execution and Output Display
CREATE backend/src/api/routes/execution.py:
  - PATTERN: Async code execution with WebSocket result streaming
  - Support multiple languages with proper timeout and resource limits
  - Implement execution history and result caching
  
CREATE frontend/src/components/Output/ConsoleOutput.tsx:
  - PATTERN: Real-time execution output display with syntax highlighting
  - Support stdout/stderr separation and error linking to code
  - Implement output clearing and download functionality

Task 10: Implement Project Sharing and Collaboration Features
CREATE backend/src/api/routes/collaboration.py:
  - PATTERN: APIs for project sharing, permissions, and collaboration
  - Support public/private projects, fork creation, and access control
  - Implement collaboration invitations and user management
  
CREATE frontend/src/components/Collaboration/ShareDialog.tsx:
  - PATTERN: UI for project sharing configuration
  - Support link sharing, permission levels, and collaboration settings
  - Implement fork creation and project template publishing

Task 11: Add Comprehensive Testing Suite
CREATE tests/backend/unit/test_container_service.py:
  - PATTERN: Unit tests for container management with mocking
  - Test security configurations, resource limits, and error handling
  - Ensure proper cleanup and container lifecycle management
  
CREATE tests/frontend/e2e/collaboration.spec.ts:
  - PATTERN: End-to-end tests for real-time collaboration
  - Test multi-user editing, cursor synchronization, and conflict resolution
  - Validate WebSocket connection handling and reconnection

Task 12: Security Hardening and Performance Optimization
CREATE backend/src/security/input_validation.py:
  - PATTERN: Comprehensive input sanitization and validation
  - Prevent code injection, XSS, and malicious file uploads
  - Implement rate limiting and abuse detection
  
CREATE infrastructure/k8s/network-policy.yaml:
  - PATTERN: Kubernetes network policies for container isolation
  - Block all external network access from execution containers
  - Allow only necessary internal service communication
```

### Per task pseudocode as needed added to each task

```python
# Task 3: Container Security Implementation
class SecureContainerService:
    async def create_execution_container(self, language: Language, code: str) -> str:
        # PATTERN: gVisor security configuration
        container_config = {
            "Image": f"{language}:alpine-secure",
            "Cmd": self._build_execution_command(language, code),
            "HostConfig": {
                "Runtime": "runsc",  # CRITICAL: Use gVisor runtime
                "Memory": 256 * 1024 * 1024,  # 256MB limit
                "CpuQuota": 10000,  # 10% CPU
                "NetworkMode": "none",  # CRITICAL: No network access
                "ReadonlyRootfs": True,  # Read-only filesystem
                "CapDrop": ["ALL"],  # Drop all capabilities
                "SecurityOpt": [
                    "no-new-privileges:true",
                    "seccomp=restricted.json"
                ],
                "Ulimits": [{"Name": "nofile", "Soft": 1024, "Hard": 1024}],
                "AutoRemove": True  # Auto-cleanup
            }
        }
        
        # GOTCHA: Always set execution timeout
        container = await self.docker_client.containers.create(**container_config)
        
        # PATTERN: Async execution with timeout
        try:
            await asyncio.wait_for(
                container.start(),
                timeout=30.0  # 30 second execution limit
            )
            return container.id
        except asyncio.TimeoutError:
            await container.kill()
            raise ExecutionTimeoutError("Code execution timed out")
            
# Task 5: Yjs Collaboration Integration
async function setupCollaboration(editor: monaco.editor.IStandaloneCodeEditor, projectId: string) {
    // PATTERN: Yjs document setup with WebSocket provider
    const ydoc = new Y.Doc();
    const provider = new WebsocketProvider(
        'wss://api.example.com/collaboration',
        projectId,
        ydoc,
        {
            connect: true,
            awareness: new awarenessProtocol.Awareness(ydoc)
        }
    );
    
    // CRITICAL: Handle connection errors and reconnection
    provider.on('status', (event: any) => {
        if (event.status === 'disconnected') {
            // Show offline indicator
            showOfflineIndicator();
        }
    });
    
    // PATTERN: Monaco binding with proper disposal
    const ytext = ydoc.getText('monaco');
    const monacoBinding = new MonacoBinding(
        ytext,
        editor.getModel()!,
        new Set([editor]),
        provider.awareness
    );
    
    // GOTCHA: Always cleanup on component unmount
    return () => {
        monacoBinding.destroy();
        provider.destroy();
    };
}

# Task 6: WebSocket Terminal Implementation  
class TerminalWebSocketHandler:
    async def handle_terminal_command(self, websocket: WebSocket, command: str):
        # PATTERN: Container command execution with streaming
        container = await self.get_user_container(websocket.user_id)
        
        # CRITICAL: Validate and sanitize command input
        sanitized_command = self.sanitize_command(command)
        
        exec_instance = await container.exec_run(
            sanitized_command,
            stdin=True,
            stdout=True,
            stderr=True,
            stream=True,
            tty=True
        )
        
        # PATTERN: Stream output to WebSocket
        async for chunk in exec_instance.output:
            if chunk:
                await websocket.send_text(chunk.decode('utf-8', errors='ignore'))
                
        # GOTCHA: Always send exit code
        exit_code = exec_instance.exit_code
        await websocket.send_json({
            'type': 'exit',
            'code': exit_code
        })
```

### Integration Points
```yaml
DATABASE:
  - migration: "Create users, projects, files, executions tables"
  - indexes: "CREATE INDEX idx_project_owner ON projects(owner_id)"
  - constraints: "Add foreign key constraints for data integrity"
  
CONFIG:
  - add to: backend/src/config/settings.py
  - pattern: "DOCKER_HOST = os.getenv('DOCKER_HOST', 'unix://var/run/docker.sock')"
  - critical: "GVISOR_RUNTIME = os.getenv('GVISOR_RUNTIME', 'runsc')"
  
FRONTEND_ROUTING:
  - add to: frontend/src/App.tsx
  - pattern: "React Router with authentication guards and lazy loading"
  - routes: "/editor/:projectId, /dashboard, /auth/login, /auth/register"
  
WEBSOCKET_ENDPOINTS:
  - add to: backend/src/websocket/manager.py
  - pattern: "WebSocket routing for terminal, collaboration, execution"
  - security: "JWT authentication for WebSocket connections"
  
CONTAINER_IMAGES:
  - build: "Multi-stage Dockerfiles for each language runtime"
  - security: "Base images with minimal attack surface"
  - optimization: "Layer caching and size optimization"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend validation
cd backend && ruff check src/ --fix
cd backend && mypy src/
cd backend && pytest tests/unit/ -v

# Frontend validation  
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run test:unit

# Expected: No errors. Fix any issues before proceeding.
```

### Level 2: Integration Tests
```bash
# Start services
docker-compose up -d postgres redis

# Test container security
cd backend && pytest tests/security/test_container_security.py -v

# Test file system operations
cd frontend && npm run test:integration

# Test collaboration features
cd tests && python test_collaboration.py

# Expected: All tests pass. Fix failing tests before proceeding.
```

### Level 3: End-to-End Testing
```bash
# Start full application
docker-compose up --build

# Run E2E tests
cd tests/e2e && npx playwright test

# Manual testing checklist:
# 1. Create account and login ✓
# 2. Create new Python project ✓  
# 3. Write and execute code ✓
# 4. Share project with collaborator ✓
# 5. Real-time collaborative editing ✓
# 6. Terminal command execution ✓
# 7. File upload and management ✓
# 8. Package installation ✓

# Performance testing
cd tests/load && python load_test.py --users=100 --duration=300s

# Expected: <5s response times, no errors under load
```

### Level 4: Security Validation
```bash
# Container escape testing
docker run --rm -it security-scanner test-container-escape

# Network isolation testing
cd tests/security && python test_network_isolation.py

# Input validation testing
cd tests/security && python test_input_validation.py

# OWASP ZAP security scan
zap-baseline.py -t http://localhost:3000

# Expected: No critical vulnerabilities, all containers properly isolated
```

## Final Validation Checklist
- [ ] All tests pass: `make test-all`
- [ ] No linting errors: `make lint-all`
- [ ] No type errors: `make type-check-all`
- [ ] Security scan passes: `make security-test`
- [ ] Performance benchmarks met: `make load-test`
- [ ] Container isolation verified: `make test-container-security`
- [ ] Real-time collaboration works: Manual test with 2+ users
- [ ] All 7 languages execute correctly: Manual verification
- [ ] File operations persist correctly: Manual verification
- [ ] Authentication and authorization work: Manual verification
- [ ] Error cases handled gracefully: Exception testing
- [ ] Documentation complete: README, API docs, deployment guide

---

## Anti-Patterns to Avoid
- ❌ Don't run containers without gVisor/Firecracker for untrusted code
- ❌ Don't allow network access from execution containers
- ❌ Don't store user code in plain text without encryption
- ❌ Don't skip input validation and sanitization
- ❌ Don't forget to implement proper container cleanup
- ❌ Don't use blocking operations in WebSocket handlers
- ❌ Don't allow unlimited file uploads or execution time
- ❌ Don't hardcode secrets or configuration values
- ❌ Don't skip rate limiting and abuse prevention
- ❌ Don't forget to implement proper error boundaries

## Confidence Score: 9/10

High confidence due to:
- Comprehensive research covering all major components
- Well-established libraries and patterns (Monaco, Yjs, Docker)
- Clear security guidelines and best practices
- Detailed validation gates with specific test scenarios
- Production-ready architecture with scalability considerations

Minor uncertainty on:
- gVisor performance impact on code execution latency
- Large-scale collaboration performance with 100+ concurrent users
- Container resource optimization for multi-language support

The implementation should succeed with careful attention to security hardening and performance optimization during the validation phases.
