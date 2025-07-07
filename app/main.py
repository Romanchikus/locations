from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import config
from app.routes import router, requests_router
from app.middleware import RequestLoggingMiddleware
from app.database import engine, Base
import logging

# Create database tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

if config.debug:
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
else:
    logging.getLogger("uvicorn").setLevel(logging.INFO)

# Create FastAPI app
app = FastAPI(
    title=config.app_name,
    version=config.app_version,
    description="Application for managing geo-locations with request tracking",
    debug=config.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Include routes
app.include_router(router)
app.include_router(requests_router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {config.app_name}",
        "version": config.app_version,
        "docs": "/docs",
        "endpoints": {"requests": "/requests"},
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": config.app_name}
