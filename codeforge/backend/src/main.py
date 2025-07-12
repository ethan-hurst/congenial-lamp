"""
CodeForge Backend - Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config.settings import settings
from .api.v1 import auth, containers, ai, clone, collaboration, debug, deployment, performance

# Create FastAPI app
app = FastAPI(
    title="CodeForge API",
    description="Revolutionary cloud development platform API",
    version="0.1.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware in production
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["codeforge.dev", "*.codeforge.dev"]
    )

# Include API routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(containers.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(clone.router, prefix="/api/v1")
app.include_router(collaboration.router, prefix="/api/v1")
app.include_router(debug.router, prefix="/api/v1")
app.include_router(deployment.router, prefix="/api/v1")
app.include_router(performance.router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if settings.is_production else str(exc)
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    print(f"Starting CodeForge API in {settings.ENVIRONMENT} mode")
    
    # Initialize services
    # TODO: Initialize database connection pool
    # TODO: Start background tasks

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    print("Shutting down CodeForge API")
    
    # Cleanup resources
    # TODO: Close database connections
    # TODO: Stop background tasks

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        workers=1 if settings.is_development else settings.WORKERS
    )