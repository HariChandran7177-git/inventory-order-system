import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from payment.app.db.postgresql import create_db_and_tables
from payment.app.routes.route import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler to initialize the database at startup.
    """
    logger.info("Payment Service is starting up...")
    try:
        await create_db_and_tables()  # Ensures tables are created on startup
        logger.info("PostgreSQL database tables initialized successfully.")
    except Exception as e:
        logger.warning(
            f"Could not connect to PostgreSQL during startup (service may be running offline/testing): {e}"
        )
    yield
    logger.info("Payment Service is shutting down...")


app = FastAPI(title="Payment Service", lifespan=lifespan)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# CORS configuration explicitly allowing frontend origins to prevent W3C credentials violation
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    Standard health check endpoint for container orchestration and uptime monitoring.
    """
    return {"status": "ok", "service": "payment"}


# Include primary validated order routes (pruned duplicate /CRUD/orders router)
app.include_router(router)


def main() -> None:
    """
    Entry point for the application when run explicitly.
    """
    print("main.py running explicitly")


if __name__ == "__main__":
    main()
