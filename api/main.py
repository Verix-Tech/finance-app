import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from dependencies.database import db_service
from routers import auth, users, transactions, limits, subscriptions, reports, health


def configure_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
    )
    # Reduce noise from libraries
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("psycopg2").setLevel(logging.ERROR)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Configure logging
    configure_logging()
    logger = logging.getLogger(__name__)

    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Finance API for managing transactions, limits, and subscriptions",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(transactions.router)
    app.include_router(limits.router)
    app.include_router(subscriptions.router)
    app.include_router(reports.router)
    app.include_router(health.router)

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        logger.info("Application starting up...")
        logger.info(
            f"Database connection status: {db_service.manager.check_connection()}"
        )

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources on application shutdown."""
        logger.info("Application shutting down...")
        db_service.shutdown()

    return app


# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_refactored:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
