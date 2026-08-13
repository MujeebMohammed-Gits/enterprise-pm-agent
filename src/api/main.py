"""
Main API application for Enterprise PM Agent
Designed to work with both traditional servers and Vercel Functions
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Optional
from datetime import datetime 

from config.settings import settings
from src.core.workflow.engine import WorkflowEngine
from persistence.storage import StorageFactory
from src.core.workflow.engine import WorkflowInstance

# Configure logging
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Global instances
workflow_engine = WorkflowEngine()
task_storage = StorageFactory.create_storage(
    "memory",
    dict,
    file_path="./data/tasks.json"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    yield
    logger.info("Shutting down application")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Project and Delivery Management Agent",
    openapi_url=f"/{settings.app_version}/openapi.json" if not settings.debug else "/openapi.json",
    docs_url=f"/{settings.app_version}/docs" if not settings.debug else "/docs",
    redoc_url=f"/{settings.app_version}/redoc" if not settings.debug else "/redoc",
    lifespan=lifespan
)

# ----------------------------------------------------
# Root Route (ONLY the code you asked for)
# ----------------------------------------------------
@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Enterprise PM Agent API is running",
        "health": "/health",
        "docs": "/docs"
    }

# Configure CORS
if settings.backend_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.backend_cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Dependency functions
async def get_workflow_engine() -> WorkflowEngine:
    return workflow_engine

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials.credentials == "invalid-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": "test-user", "username": "testuser", "permissions": ["*"]}

# Health check endpoint
@app.get("/health", tags=["monitoring"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat()
    }

# Version endpoint
@app.get("/version", tags=["monitoring"])
async def version():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env
    }

# Workflow endpoints
@app.post("/workflows/start", tags=["workflows"])
async def start_workflow(
    workflow_id: str,
    entity_id: str,
    context: Optional[dict] = None,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user: dict = Depends(get_current_user)
):
    try:
        instance_id = await workflow_engine.start_workflow(
            workflow_id,
            entity_id,
            context
        )
        return {
            "success": True,
            "instance_id": instance_id,
            "message": "Workflow started successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@app.post("/workflows/{instance_id}/transition", tags=["workflows"])
async def transition_workflow(
    instance_id: str,
    transition_id: str,
    context: Optional[dict] = None,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user: dict = Depends(get_current_user)
):
    try:
        success = await workflow_engine.transition(
            instance_id,
            transition_id,
            user_id=current_user["user_id"],
            context=context
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transition could not be executed - conditions not met or unauthorized"
            )
        return {"success": True, "message": "Transition executed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing transition: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@app.get("/workflows/{instance_id}/transitions", tags=["workflows"])
async def get_available_transitions(
    instance_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user: dict = Depends(get_current_user)
):
    try:
        transitions = await workflow_engine.get_available_transitions(
            instance_id,
            user_id=current_user["user_id"]
        )
        return {"success": True, "transitions": transitions}
    except Exception as e:
        logger.error(f"Error getting available transitions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@app.get("/workflows/{instance_id}", tags=["workflows"])
async def get_workflow_instance(
    instance_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    current_user: dict = Depends(get_current_user)
):
    instance = workflow_engine.workflow_instances.get(instance_id)
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow instance not found")

    return {
        "success": True,
        "data": {
            "id": instance.id,
            "workflow_id": instance.workflow_id,
            "entity_id": instance.entity_id,
            "current_state": instance.current_state,
            "context": instance.context,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
            "completed_at": instance.completed_at.isoformat() if instance.completed_at else None
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1
    )
