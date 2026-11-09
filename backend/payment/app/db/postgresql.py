import importlib
import os
import pkgutil
from typing import Annotated, AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from payment.app.models import models  # noqa: F401

load_dotenv()

# Provide robust fallback defaults so the engine does not fail on startup when .env is absent
POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "postgres")

URL_ASYNC_DATABASE = URL.create(
    "postgresql+asyncpg",
    username=POSTGRES_USERNAME,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    database=POSTGRES_DATABASE,
)

SQL_ECHO = os.getenv("SQL_ECHO", "false").strip().lower() == "true"
async_engine = create_async_engine(URL_ASYNC_DATABASE, echo=SQL_ECHO)

import payment.app.models as models_pkg


def import_models():
    """
    Dynamically imports all modules in the 'models' package.
    """
    for _, module_name, _ in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"payment.app.models.{module_name}")


async def create_db_and_tables() -> None:
    """
    Creates the database and all associated tables if they do not already exist.

    This function dynamically imports all models using the `import_models` function
    and then utilizes SQLModel's metadata to create the necessary database schema
    by binding it to the specified engine.
    """
    import_models()  # Dynamically import all models
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provides an async generator function yielding an AsyncSession for database operations.
    """
    async with AsyncSession(async_engine) as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]
