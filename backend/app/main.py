"""
ANCHOR - Main FastAPI Application Entry Point
Sovereign Digital Account Layer for Bahamians
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.api import accounts, vault, recovery, attestations, auth


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="Sovereign Digital Account Layer - A persistent, recoverable financial and civic anchor for Bahamians",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(vault.router, prefix="/api/vault", tags=["Vault"])
app.include_router(recovery.router, prefix="/api/recovery", tags=["Recovery"])
app.include_router(attestations.router, prefix="/api/attestations", tags=["Attestations"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Sovereign Digital Account Layer for Bahamians",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

