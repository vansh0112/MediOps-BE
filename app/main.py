import logging
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import app.config.cloudinary
from app.api.v1.auth import router as auth_router
from app.api.v1.patients import router as patients_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI(
    description="Medicare AI Assistant",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(patients_router, prefix="/api/v1/patients")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """Log 422 validation errors so you can see the reason in the terminal."""
    errors = exc.errors()
    log = logging.getLogger("app.main")
    log.warning("422 Validation error: %s", errors)
    return JSONResponse(
        status_code=422,
        content={"detail": errors, "message": "Validation failed. Send multipart/form-data with required fields."},
    )


@app.get("/")
async def root(request: Request):
    """Root endpoint returning basic API information."""
    return {"name": "Medicare AI Assistant", "version": "0.1.0", "status": "healthy"}


@app.get("/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint returning basic API information."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (Render provides this)
    port = int(os.getenv("PORT", 8000))
    
    # Bind to 0.0.0.0 for Render.com compatibility
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )