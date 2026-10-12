"""
Main Application Entrypoint for Secure Online Code Execution Platform.
Team 14 - Software Engineering Mini-Project
PES University
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import PROJECT_INFO, STATIC_DIR
from app.logger import log_event, logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log_event("SERVER_STARTUP", details={"team": PROJECT_INFO["team"], "version": PROJECT_INFO["version"]})
    yield
    # Shutdown
    log_event("SERVER_SHUTDOWN")

# Create FastAPI App with Lifespan
app = FastAPI(
    title=PROJECT_INFO["title"],
    description="Isolated runtime for secure multi-language code execution with strict resource limits.",
    version=PROJECT_INFO["version"],
    lifespan=lifespan,
)

# Enable CORS for local and web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global safe exception handler (SCEP-F-018, SCEP-NF-006, TC-SEC-07)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal error processing {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "An internal server error occurred. Please try again later.",
            "category": "internal_server_error",
        },
    )

# Register API Router
app.include_router(api_router)

# Mount Static Files
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve website favicon."""
    fav_path = STATIC_DIR / "favicon.svg"
    if fav_path.exists():
        return FileResponse(str(fav_path), media_type="image/svg+xml")
    return Response(status_code=204)

@app.get("/", include_in_schema=False)
async def serve_home():
    """Serve the primary Web UI IDE."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=200,
        content={"message": "Secure Online Code Execution Platform API is running. Web UI loading..."},
    )
