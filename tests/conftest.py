import asyncio
from contextlib import asynccontextmanager
import fnmatch
import os
import sys
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import warnings

# Suppress third-party library deprecation warnings from redis-om and pydantic
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Ensure backend microservices are always resolvable without requiring pytest.ini
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from inventory.app.db.redis import CustomJsonCoder
from inventory.app.main import app as inventory_app
from inventory.app.models.models import Product
from payment.app.db.postgresql import get_db
from payment.app.main import app as payment_app
from payment.app.models.models import Order


class MockAsyncRedisClient:
    """In-memory async Redis client for caching that is safe across event loops."""

    def __init__(self):
        self.data: Dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self.data[key] = value

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self.data.pop(k, None)

    async def scan_iter(self, match: str = "*"):
        for k in list(self.data.keys()):
            if fnmatch.fnmatch(k, match):
                yield k

    async def close(self) -> None:
        pass


class MockRedisBackend(RedisBackend):
    """Event-loop independent RedisBackend for FastAPICache."""

    def __init__(self):
        self.redis = MockAsyncRedisClient()

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[str]]:
        val = await self.redis.get(key)
        return (600, val) if val is not None else (0, None)

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        await self.redis.set(key, value, ex=expire)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if key:
            await self.redis.delete(key)
            return 1
        elif namespace:
            count = 0
            async for k in self.redis.scan_iter(f"*{namespace}*"):
                await self.redis.delete(k)
                count += 1
            return count
        self.redis.data.clear()
        return 0


class MockAsyncSession:
    """
    In-memory isolated mock for SQLModel/SQLAlchemy AsyncSession.
    Implements all operations required by Payment Service without requiring a live PostgreSQL daemon.
    """

    def __init__(self, storage: Optional[Dict[int, Order]] = None):
        self.orders: Dict[int, Order] = storage if storage is not None else {}
        self._next_id = max(self.orders.keys(), default=0) + 1
        self._pending_adds: List[Order] = []

    def add(self, instance: Order) -> None:
        if instance.order_id is None:
            instance.order_id = self._next_id
            self._next_id += 1
        self._pending_adds.append(instance)

    async def commit(self) -> None:
        for inst in self._pending_adds:
            self.orders[inst.order_id] = inst
        self._pending_adds.clear()

    async def refresh(self, instance: Order) -> None:
        if instance.order_id in self.orders:
            saved = self.orders[instance.order_id]
            for field in instance.model_fields.keys():
                setattr(instance, field, getattr(saved, field))

    async def get(self, entity_class, ident: int) -> Optional[Order]:
        return self.orders.get(int(ident))

    async def exec(self, statement):
        mock_result = MagicMock()
        statement_str = str(statement).lower()
        all_orders = list(self.orders.values())

        # Check if query is filtering for a specific order_id
        filtered = all_orders
        for order_id, order in self.orders.items():
            if f"order_id = {order_id}" in statement_str or f"order.order_id = {order_id}" in statement_str:
                filtered = [order]
                break

        mock_result.all.return_value = filtered
        mock_result.first.return_value = filtered[0] if filtered else None
        return mock_result

    async def execute(self, statement):
        mock_exec = MagicMock()
        statement_str = str(statement).lower()
        all_orders = list(self.orders.values())
        mock_exec.scalars.return_value.first.return_value = all_orders[0] if all_orders else None
        mock_exec.first.return_value = all_orders[0] if all_orders else None
        return mock_exec

    async def delete(self, instance: Order) -> None:
        self.orders.pop(instance.order_id, None)

    async def rollback(self) -> None:
        self._pending_adds.clear()

    async def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def setup_isolated_test_env():
    """
    Automatically configures isolated in-memory Redis, FastAPICache, and Database for all tests.
    Prevents tests from attempting socket connections to external localhost daemons.
    """
    fake_sync_redis = fakeredis.FakeRedis(decode_responses=True)
    mock_cache_backend = MockRedisBackend()

    # Configure Redis OM to use fake sync client
    Product.set_meta_attr(fake_sync_redis, global_key_prefix="inventory_order_system", model_key_prefix="inventory.Product")

    # Configure FastAPICache with our event-loop independent mock backend
    FastAPICache.init(mock_cache_backend, prefix="fastapi-cache", coder=CustomJsonCoder)

    # Override Inventory lifespan to prevent live Redis connection attempts
    @asynccontextmanager
    async def dummy_inventory_lifespan(application):
        application.state.redis = fake_sync_redis
        Product.set_meta_attr(fake_sync_redis, global_key_prefix="inventory_order_system", model_key_prefix="inventory.Product")
        FastAPICache.init(mock_cache_backend, prefix="fastapi-cache", coder=CustomJsonCoder)
        yield

    inventory_app.router.lifespan_context = dummy_inventory_lifespan

    # Suppress Payment DB lifespan startup/shutdown hooks
    @asynccontextmanager
    async def dummy_payment_lifespan(application):
        yield

    payment_app.router.lifespan_context = dummy_payment_lifespan

    # Suppress background task delay and postgres connection
    async def dummy_process_order(order_id: int):
        pass

    with patch("payment.app.services.process_service.ProcessService.process_order", side_effect=dummy_process_order), \
         patch("payment.app.services.stream_service.get_redis_stream_client", return_value=fake_sync_redis), \
         patch("payment.app.db.redis_stream.get_redis_stream_client", return_value=fake_sync_redis), \
         patch("inventory.app.db.redis.get_redis_om_client", return_value=fake_sync_redis), \
         patch("inventory.app.db.redis.get_redis_cache_client", return_value=mock_cache_backend.redis), \
         patch("inventory.app.main.get_redis_om_client", return_value=fake_sync_redis), \
         patch("inventory.app.main.get_redis_cache_client", return_value=mock_cache_backend.redis):
        yield {
            "fake_sync_redis": fake_sync_redis,
            "mock_cache_backend": mock_cache_backend,
        }

    # Clean up FastAPICache
    FastAPICache.reset()


@pytest.fixture
def fake_redis(setup_isolated_test_env):
    """Provides direct access to the isolated fake sync Redis instance."""
    return setup_isolated_test_env["fake_sync_redis"]


@pytest.fixture
def mock_session():
    """Provides a fresh isolated MockAsyncSession instance."""
    return MockAsyncSession()


@pytest.fixture
def inventory_client():
    """TestClient for the Inventory Service API."""
    with TestClient(inventory_app) as client:
        yield client


@pytest.fixture
def payment_client(mock_session):
    """
    TestClient for the Payment Service API with overridden database session.
    """
    async def override_get_db() -> AsyncGenerator[MockAsyncSession, None]:
        yield mock_session

    payment_app.dependency_overrides[get_db] = override_get_db

    with TestClient(payment_app) as client:
        yield client

    payment_app.dependency_overrides.clear()


@pytest.fixture
def integrated_client(mock_session, inventory_client, fake_redis):
    """
    Payment TestClient configured with an in-process transport to the Inventory Service.
    When Payment calls http://127.0.0.1:8000/inventory/..., it routes directly
    to the in-memory inventory_app without requiring live network ports.
    """
    async def override_get_db() -> AsyncGenerator[MockAsyncSession, None]:
        yield mock_session

    payment_app.dependency_overrides[get_db] = override_get_db

    # Create an in-process ASGI transport client for inter-service communication
    asgi_transport = httpx.ASGITransport(app=inventory_app)

    original_async_client = httpx.AsyncClient

    def mocked_async_client(*args, **kwargs):
        kwargs["transport"] = asgi_transport
        kwargs["base_url"] = "http://127.0.0.1:8000"
        return original_async_client(*args, **kwargs)

    with patch("httpx.AsyncClient", side_effect=mocked_async_client):
        with TestClient(payment_app) as client:
            yield client

    payment_app.dependency_overrides.clear()
