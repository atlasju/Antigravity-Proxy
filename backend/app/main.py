from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ag/backend/
LOG_FILE = os.path.join(LOG_DIR, "antigravity.log")

# Create rotating file handler (10MB per file, keep 5 backups)
file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))

# Also keep console output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

# Reduce noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {LOG_FILE}")

app = FastAPI(
    title="Antigravity API",
    description="Python Backend for Antigravity Manager",
    version="4.0.0"
)

# Configure CORS
origins = [
    "http://localhost:5173",  # Vite Dev Server
    "http://127.0.0.1:5173",
    "*",  # Allow all origins for API proxy usage
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Key validation middleware for proxy routes
class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate API key for proxy routes (/v1/*, /v1beta/*)."""
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        # Skip OPTIONS requests (CORS preflight)
        # Fix double /v1beta prefix (common client configuration error)
        # Fix double /v1beta prefix (common client configuration error)
        if path.startswith("/v1beta/v1beta"):
            new_path = path.replace("/v1beta/v1beta", "/v1beta", 1)
            print(f"[Path Fix] Rewriting {path} -> {new_path}")
            request.scope["path"] = new_path
            path = new_path
        
        # Only validate proxy routes
        if path.startswith("/v1") or path.startswith("/v1beta"):
            from app.core.auth import get_user_by_api_key
            
            # Extract API key from Authorization header
            auth_header = request.headers.get("Authorization", "")
            x_goog_api_key = request.headers.get("x-goog-api-key", "")
            api_key = None
            
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            elif "x-api-key" in request.headers:
                api_key = request.headers.get("x-api-key")
            elif x_goog_api_key:
                # Gemini SDK uses x-goog-api-key header
                api_key = x_goog_api_key
            
            if not api_key:
                # Check query parameter for Gemini SDK compatibility
                api_key = request.query_params.get("key")
            
            if api_key:
                user = get_user_by_api_key(api_key)
                if user:
                    # Valid API key, proceed
                    return await call_next(request)
            
            # Invalid or missing API key
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"}
            )
        
        return await call_next(request)


app.add_middleware(APIKeyMiddleware)


@app.get("/health")
async def health_check():
    from app.core.token_manager import get_token_manager
    manager = get_token_manager()
    return {
        "status": "ok", 
        "version": "4.0.0",
        "accounts_loaded": manager.pool_size
    }

from app.core.database import create_db_and_tables
from app.core.token_manager import init_token_manager, get_token_manager
from app.api import routes_management, routes_openai, routes_claude, routes_import, routes_gemini, routes_oauth, routes_quota, routes_auth, routes_mapping, routes_images, routes_stats


# Background task for token refresh (every 240 seconds)
async def background_token_refresh():
    """Background task to refresh tokens before they expire."""
    while True:
        try:
            await asyncio.sleep(240)  # Check every 4 minutes
            
            manager = get_token_manager()
            if manager.pool_size > 0:
                print("[Scheduler] Running token refresh check...")
                await manager.refresh_all_expiring_tokens()
        except Exception as e:
            print(f"[Scheduler] Error in token refresh: {e}")


# Background task for quota updates (every 10 minutes)
async def background_quota_update():
    """Background task to update account quotas for smart routing."""
    # Initial delay to let tokens initialize
    await asyncio.sleep(30)
    
    while True:
        try:
            manager = get_token_manager()
            if manager.pool_size > 0:
                print("[Scheduler] Running quota update...")
                await manager.update_quotas()
        except Exception as e:
            print(f"[Scheduler] Error in quota update: {e}")
        
        await asyncio.sleep(600)  # Every 10 minutes


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    # Initialize TokenManager with accounts from database
    await init_token_manager()
    # Start background token refresh task
    asyncio.create_task(background_token_refresh())
    print("[Scheduler] Background token refresh started (240s interval)")
    # Start background quota update task
    asyncio.create_task(background_quota_update())
    print("[Scheduler] Background quota update started (600s interval)")

# Auth APIs (no authentication required for login)
app.include_router(routes_auth.router, prefix="/api/auth", tags=["Auth"])

# Management APIs
app.include_router(routes_management.router, prefix="/api/accounts", tags=["Accounts"])

# Token Import APIs (for web deployment)
app.include_router(routes_import.router, prefix="/api/import", tags=["Import"])

# OAuth APIs (for web-based authorization)
app.include_router(routes_oauth.router, prefix="/api/oauth", tags=["OAuth"])

# Quota & Pool APIs
app.include_router(routes_quota.router, prefix="/api/quota", tags=["Quota"])

# OpenAI-compatible Proxy APIs
app.include_router(routes_openai.router, prefix="/v1", tags=["OpenAI Proxy"])

# Claude/Anthropic-compatible Proxy APIs  
app.include_router(routes_claude.router, prefix="/v1", tags=["Claude Proxy"])

# Gemini Native Proxy APIs (for Google SDK)
app.include_router(routes_gemini.router, prefix="/v1beta", tags=["Gemini Proxy"])

# Model Mapping APIs
app.include_router(routes_mapping.router, prefix="/api/mappings", tags=["Model Mappings"])

# Image Generation APIs (OpenAI Compatible)
app.include_router(routes_images.router, prefix="/v1/images", tags=["Image Generation"])

# Statistics APIs
app.include_router(routes_stats.router, prefix="/api", tags=["Statistics"])

# Serve frontend static files in production
# This avoids CORS issues and simplifies deployment
FRONTEND_DIST = os.environ.get("AG_FRONTEND_DIST", None)
if FRONTEND_DIST and os.path.exists(FRONTEND_DIST):
    logger.info(f"Serving static files from: {FRONTEND_DIST}")
    # Mount assets directory
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_DIST}/assets"), name="assets")
    
    # SPA fallback: serve index.html for any other route
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't catch API routes (they are already handled above)
        if full_path.startswith("api/") or full_path.startswith("v1/") or full_path.startswith("v1beta/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
            
        index_path = f"{FRONTEND_DIST}/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend index.html not found")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
