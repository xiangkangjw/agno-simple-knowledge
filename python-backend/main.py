"""FastAPI server for the Knowledge Management System."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.routes import chat, documents, system, operations
from core.config import config
from core.knowledge_system import KnowledgeSystem

# Set up logging
logging.basicConfig(level=config.log_level)
if config.enable_debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    logging.getLogger("agno").setLevel(logging.DEBUG)
    logging.getLogger("agno-team").setLevel(logging.DEBUG)
    os.environ.setdefault("AGNO_DEBUG", "true")
else:
    logging.getLogger("uvicorn").setLevel(config.log_level)
    logging.getLogger("uvicorn.error").setLevel(config.log_level)
    logging.getLogger("uvicorn.access").setLevel(config.log_level)
    logging.getLogger("agno").setLevel(config.log_level)
    logging.getLogger("agno-team").setLevel(config.log_level)

logger = logging.getLogger(__name__)

# Global knowledge system instance
knowledge_system: KnowledgeSystem = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global knowledge_system

    # Startup
    logger.info("Starting Knowledge Management System API...")
    try:
        knowledge_system = KnowledgeSystem()
        await knowledge_system.initialize()
        app.state.knowledge_system = knowledge_system
        logger.info("Knowledge system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize knowledge system: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Knowledge Management System API...")
    if knowledge_system:
        await knowledge_system.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Knowledge Management System API",
    description="A local-first document search and chat system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],  # Tauri dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(operations.router, prefix="/api", tags=["operations"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Knowledge Management System API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "API is running"}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=config.log_level_name.lower(),
        log_config=None,
    )
