import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from loguru import logger

from inventory.app.db.redis import CustomJsonCoder, get_redis_cache_client, get_redis_om_client
from inventory.app.models.models import Product
from inventory.app.routes.route import router

# Initialize a variable to store the redis_cache instance
redis_cache = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for application startup and shutdown.
    """
    global redis_cache
    logger.info("Inventory Service is starting up...")

    # Initialize Redis OM client for data operations
    app.state.redis = get_redis_om_client()

    # Initialize Redis client for caching, set coder for reading from cache
    redis_cache = get_redis_cache_client()
    FastAPICache.init(RedisBackend(redis_cache),
                      prefix="fastapi-cache", coder=CustomJsonCoder)

    # Set model Redis database and prefix in meta
    Product.set_meta_attr(
        app.state.redis, global_key_prefix="inventory_order_system", model_key_prefix="inventory.Product")
    logger.debug("Redis connection initialized and stored in app.state")

    yield

    logger.info("Inventory Service is shutting down...")
    if hasattr(app.state, "redis") and app.state.redis:
        app.state.redis.close()
    if redis_cache:
        await redis_cache.close()
    logger.debug("Redis connection closed during app shutdown")


# Create an instance of the FastAPI application with modernized lifespan
app = FastAPI(title="Inventory Service", lifespan=lifespan)

cors_origins_env = os.getenv("CORS_ORIGINS", "")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()] or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

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
    return {"status": "ok", "service": "inventory"}


# Include inventory routes
app.include_router(router)


def main() -> None:
    """
    Entry point for the application when run explicitly.
    """
    print("main.py running explicitly")


if __name__ == "__main__":
    main()
