# 🚀 CodeForge - The Future of Cloud Development

**CodeForge** is a revolutionary cloud development platform designed to be "10x better than Replit". It features unlimited projects, zero cold starts, multi-agent AI development assistants, transparent credit-based pricing, and universal IDE support.

## 🌟 Key Features

### ✅ Implemented Features

- **🖥️ Web-Based IDE**
  - Monaco editor with multi-tab support
  - File tree explorer with drag-and-drop
  - Integrated terminal with WebSocket communication
  - Real-time code execution with output streaming
  - Syntax highlighting for 50+ languages

- **🐳 Container-Based Execution**
  - Secure Docker containers for each project
  - Support for Python, Node.js, Go (more coming)
  - Resource isolation and limits
  - Hot reload support

- **🤖 AI Integration**
  - AI chat assistant powered by multiple models
  - Code completion and suggestions
  - Basic code generation

- **🔐 Authentication & Security**
  - JWT-based authentication
  - OAuth integration (GitHub, Google)
  - Container security with isolation
  - Secure WebSocket connections

- **💳 Credits System**
  - Pay-per-use pricing model
  - Free tier with $5 monthly credits
  - Usage tracking and billing

- **📁 File Management**
  - IndexedDB storage for offline support
  - File synchronization between frontend and backend
  - In-memory storage for development (no DB required)

- **🚀 Basic Deployment**
  - Deploy to cloud providers
  - Environment variable management
  - Simple deployment tracking

### 🚧 Features In Progress

- **🗄️ Database Provisioning** - Instant PostgreSQL/MySQL with branching
- **🤖 Multi-Agent AI System** - Feature Builder, Test Writer, and Refactor agents
- **🌐 Infrastructure Management** - Custom domains, SSL, CDN, edge deployment
- **📊 Monitoring & Analytics** - Prometheus, Grafana, distributed tracing
- **🔄 CI/CD Pipelines** - Visual pipeline builder with caching
- **🏢 Enterprise Features** - SSO, audit logs, private cloud deployment
- **⚡ Instant Cloning** - <1 second environment duplication
- **🛍️ Marketplace** - Templates, bounties, revenue sharing
- **🔌 IDE Bridge** - VS Code, JetBrains, Vim/Neovim support
- **🌍 Global Edge Execution** - Deploy to 300+ edge locations

## 🚀 Quick Start

### Prerequisites

- Docker installed on your system
- Node.js 18+ and npm/yarn
- Python 3.11+ (for backend development)

### Running Locally (No Database Required!)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/codeforge.git
   cd codeforge
   ```

2. **Build Docker images for code execution**
   ```bash
   cd codeforge/docker
   chmod +x build_images.sh
   ./build_images.sh
   ```

3. **Start the backend**
   ```bash
   cd codeforge/backend
   
   # Create virtual environment
   python -m venv venv_linux
   source venv_linux/bin/activate  # On Windows: venv_linux\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Copy development environment variables
   cp .env.development .env
   
   # Run the backend (uses in-memory storage by default)
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Start the frontend**
   ```bash
   cd codeforge/frontend
   
   # Install dependencies
   npm install
   
   # Start development server
   npm run dev
   ```

5. **Access CodeForge**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Default Demo Account
- Email: `demo@codeforge.dev`
- Password: `demo123`

## 🏗️ Architecture

```
codeforge/
├── frontend/               # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── services/      # API and storage services
│   │   ├── hooks/         # React hooks
│   │   └── pages/         # Application pages
│   └── public/
│
├── backend/               # FastAPI + Python
│   ├── src/
│   │   ├── api/v1/       # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── models/       # Data models
│   │   ├── storage/      # Storage adapters
│   │   └── auth/         # Authentication
│   └── tests/
│
└── docker/               # Docker configurations
    └── images/          # Language runtime images
```

## 💻 Development

### Backend Development

The backend uses FastAPI and supports both in-memory storage (for development) and database storage (for production).

```bash
# Run tests
pytest

# Format code
black .

# Lint code
ruff check .
```

### Frontend Development

The frontend uses React with TypeScript and Vite for fast development.

```bash
# Run tests
npm test

# Build for production
npm run build

# Type check
npm run type-check
```

### Environment Variables

See `.env.development` for all available configuration options. Key variables:

- `USE_MEMORY_STORAGE=true` - Use in-memory storage (no DB required)
- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `CORS_ORIGINS` - Allowed CORS origins

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow

1. Read `PLANNING.md` for architecture and design decisions
2. Check `TASK.md` for current tasks and priorities
3. Create a feature branch
4. Make your changes following the coding standards
5. Write tests for new functionality
6. Submit a pull request

## 📊 Project Status

### Current Progress: ~25% Complete

**✅ Core Infrastructure** - Basic IDE, file system, authentication
**🚧 In Progress** - Database provisioning, multi-agent AI, monitoring
**📋 Planned** - Enterprise features, marketplace, global edge deployment

### Roadmap

**Phase 1 (Current)** - MVP with core IDE functionality
**Phase 2** - Database provisioning, advanced AI, monitoring
**Phase 3** - Enterprise features, marketplace
**Phase 4** - Global edge execution, advanced optimizations

## 🔒 Security

- All code execution happens in isolated Docker containers
- JWT-based authentication with secure token handling
- Container security with resource limits and isolation
- Planned: SOC2 compliance, end-to-end encryption

## 💰 Pricing Model

- **Free Tier**: $5 in credits every month
- **Pay-As-You-Go**: Only pay for actual compute used
- **Earn Credits**: Contribute to templates, fix bugs, help others
- **Transparent Pricing**: See exactly what you're paying for

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Inspired by the need for a better cloud development experience
- Built with modern technologies and best practices
- Designed to be developer-first and community-driven

---

**Note**: This is an ambitious project in active development. Many features are still being implemented. See the [project board](https://github.com/your-org/codeforge/projects) for current status and roadmap.