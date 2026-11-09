import os

import redis.asyncio
from dotenv import load_dotenv
from fastapi_cache.coder import JsonCoder
from loguru import logger
from redis_om import get_redis_connection

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

params = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "decode_responses": True,
}
if REDIS_PASSWORD:
    params["password"] = REDIS_PASSWORD
logger.debug(
    f"""
             Redis Connection Params in FastAPI:
             REDIS_HOST: {REDIS_HOST}
             REDIS_PORT: {REDIS_PORT}
             """
)


def get_redis_om_client(**kwargs):
    """
    Get the Redis client connection for Redis OM.
    Accepts optional keyword arguments to override or supplement default connection parameters.
    """
    conn_params = dict(params)
    conn_params.update(kwargs)
    return get_redis_connection(**conn_params)


def get_redis_cache_client():
    """
    Get the Redis cache client connection.
    """
    redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}"
    kwargs = {"encoding": "utf8", "decode_responses": True}
    if REDIS_PASSWORD:
        kwargs["password"] = REDIS_PASSWORD
    return redis.asyncio.from_url(redis_url, **kwargs)


def get_redis_stream_client():
    """
    Get the Redis client connection for streaming.
    """
    return get_redis_connection(**params)


class CustomJsonCoder(JsonCoder):
    """
    A custom JSON coder that extends the functionality of the JsonCoder class
    to ensure proper encoding and decoding of JSON data with UTF-8 support.
    Methods:
        encode(value):
            Encodes the given value into a JSON-compatible format, ensuring
            the result is in bytes if it is a string.
        decode(value):
            Decodes the given value from a JSON-compatible format, ensuring
            it is properly converted from bytes to a string if necessary.
            Raises a TypeError if the value is not a string or bytes.
    """

    @classmethod
    def encode(cls, value):
        encoded_value = super().encode(value)
        if isinstance(encoded_value, str):
            return encoded_value.encode("utf-8")  # Ensure bytes
        return encoded_value

    @classmethod
    def decode(cls, value):
        if isinstance(value, bytes):
            value = value.decode("utf-8")  # Ensure it's a string
        elif not isinstance(value, str):
            raise TypeError("Value must be a string or bytes")
        return super().decode(value.encode("utf-8") if isinstance(value, str) else value)


if __name__ == "__main__":
    load_dotenv()

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    cli_params = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "decode_responses": True,
    }
    if REDIS_PASSWORD:
        cli_params["password"] = REDIS_PASSWORD

    redis_db = get_redis_om_client(**cli_params)
    print(redis_db.ping())
