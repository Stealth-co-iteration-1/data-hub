"""FastAPI application with lifespan for database connection management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from src.config.settings import settings
from src.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - logging, DB connection pool.

    Creates the SQLAlchemy engine at startup, disposes at shutdown.
    Engine and session factory stored in app.state for dependency injection.
    """
    # Configure logging first (before any log calls)
    configure_logging()

    engine: AsyncEngine = create_async_engine(
        settings.database_url,
        echo=settings.env == "development",
    )
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    yield
    await engine.dispose()


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
