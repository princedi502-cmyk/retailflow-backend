from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
from app.core.error_handlers import setup_error_handlers
from app.core.security_logger import setup_security_logging
from app.core.request_validation_middleware import add_request_validation_middleware

from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.router import auth, products, orders, analytics, supplier, db_performance, cache_management, websocket
from app.core.config import settings
from app.core.cache import cache_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup security logging
    setup_security_logging()
    
    await connect_to_mongo()
    
    # Initialize cache manager
    await cache_manager.connect()
    
    # Initialize database monitoring (safe mode)
    try:
        from app.core.db_monitor import get_database_monitor
        from app.db.mongodb import db_manager
        
        monitor = get_database_monitor(db_manager.client)
        config = monitor.config
        
        # Only start monitoring if enabled and in safe mode
        if config.get("enable_stats", True) and config.get("safe_mode", True):
            print("Database monitoring initialized in safe mode")
            # Don't auto-start continuous monitoring - let user control it
        else:
            print("Database monitoring disabled or safe mode off")
    except Exception as e:
        print(f"Failed to initialize database monitoring: {e}")
    
    yield
    
    # Cleanup monitoring on shutdown
    try:
        from app.core.db_monitor import get_database_monitor
        from app.db.mongodb import db_manager
        monitor = get_database_monitor(db_manager.client)
        if monitor.is_monitoring:
            await monitor.stop_continuous_monitoring()
            print("Database monitoring stopped")
    except Exception as e:
        print(f"Error stopping database monitoring: {e}")
    
    # Disconnect cache manager
    await cache_manager.disconnect()
    
    await close_mongo_connection()


app = FastAPI(
    title="RetailFlow API",
    version="1.0.0",
    lifespan=lifespan
)

# Setup error handlers
setup_error_handlers(app)

# Add request validation middleware
add_request_validation_middleware(app)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Trusted hosts for production
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )

# CORS configuration - Fixed to restrict headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "CONNECT"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Sec-WebSocket-Key",
        "Sec-WebSocket-Version",
        "Sec-WebSocket-Protocol",
        "Sec-WebSocket-Accept",
        "Connection",
        "Upgrade"
    ],
)

# Response compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {"status": "ok"} 

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(analytics.router)
app.include_router(supplier.router)
app.include_router(db_performance.router)
app.include_router(cache_management.router)
app.include_router(websocket.router)


@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "database": "connected",
        "version": "1.0.0"
    }