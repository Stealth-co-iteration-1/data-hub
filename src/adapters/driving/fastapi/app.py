"""FastAPI application with lifespan for database connection management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.driven.repository_factory import create_repository
from src.config.settings import settings
from src.observability.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - logging, DB connection pool, repository.

    Creates the repository via factory at startup, disposes engine at shutdown.
    Repository, engine, and backend type stored in app.state for dependency injection.
    """
    # Configure logging first (before any log calls)
    configure_logging()

    # Create repository bundle via factory (detects backend from URL scheme)
    bundle = create_repository(
        settings.database_url,
        echo=settings.env == "development",
    )

    # Store in app.state for dependency injection
    app.state.repository = bundle.repository
    app.state.engine = bundle.engine
    app.state.session_factory = None  # Deprecated - use repository directly
    app.state.backend = bundle.backend

    logger.info(
        "startup_complete",
        backend=bundle.backend,
        database_url_scheme=settings.database_url.split("://")[0],
    )

    yield

    await bundle.engine.dispose()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Data Hub",
    description="Webhook ingestion platform with strict validation",
    version=settings.version,
    lifespan=lifespan,
)


def configure_middleware() -> None:
    """Configure application middleware.

    Order matters - middleware runs in reverse order of registration.
    CorrelationIdMiddleware should be outermost (registered first).
    """
    from .middleware import CorrelationIdMiddleware

    app.add_middleware(CorrelationIdMiddleware)


def configure_routes() -> None:
    """Configure application routes.

    Called after app is fully initialized.
    """
    from .routes.health import router as health_router
    from .routes.metrics import router as metrics_router
    from .routes.webhook import router as webhook_router

    app.include_router(webhook_router)
    app.include_router(health_router)
    app.include_router(metrics_router)


# Configure in order: middleware first, then routes
configure_middleware()
configure_routes()
