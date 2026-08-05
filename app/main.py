"""
Main application entry point for Enterprise PM Agent
"""
import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.core.workflow.engine import workflow_engine, register_default_workflows

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Project and Delivery Management Agent",
    docs_url="/docs" if not settings.debug else None,
    redoc_url="/redoc" if not settings.debug else None
)

# Set up CORS middleware
if settings.security.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.security.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers (will be implemented later)
# For now, we'll create basic endpoints directly

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat()
    }

# Version endpoint
@app.get("/version")
async def version():
    """Version information endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs" if not settings.debug else None
    }

# Workflow endpoints (basic implementations)
@app.get("/workflows")
async def list_workflows():
    """List available workflow templates"""
    workflows = workflow_engine.list_workflows()
    return {
        "workflows": [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "methodology": wf.methodology,
                "version": wf.version
            }
            for wf in workflows
        ]
    }

@app.post("/workflows/start")
async def start_workflow(
    workflow_id: str,
    entity_id: str,
    context: dict = None
):
    """Start a new workflow instance"""
    try:
        instance_id = await workflow_engine.start_workflow(
            workflow_id,
            entity_id,
            context or {}
        )
        return {
            "success": True,
            "instance_id": instance_id,
            "message": "Workflow started successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

# Import HTTPException here to avoid circular imports
from fastapi import HTTPException

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers
    )