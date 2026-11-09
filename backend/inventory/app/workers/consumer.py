import asyncio
import os

import redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from loguru import logger

from inventory.app.db.redis import CustomJsonCoder, get_redis_cache_client, get_redis_om_client
from inventory.app.models.models import Product
from inventory.app.services.stream_service import StreamService
from inventory.app.services.utils import clear_cache_by_pk

STREAM_KEY = os.getenv("INVENTORY_STREAM_KEY", "order_completed")
CONSUMER_GROUP = os.getenv("INVENTORY_CONSUMER_GROUP", "inventory_group")
CONSUMER_NAME = os.getenv("INVENTORY_CONSUMER_NAME", "inventory_consumer_1")

# Redis Lua script for concurrency-safe atomic stock decrement
# Returns:
#   >= 0 : Remaining stock after atomic decrement (success)
#   -1   : Product or quantity key not found in inventory
#   -2   : Insufficient stock (current < requested)
#   -3   : Invalid order quantity (order_qty <= 0)
LUA_ATOMIC_DECREMENT = """
local key = KEYS[1]
local order_qty = tonumber(ARGV[1])

if not order_qty or order_qty <= 0 then
    return -3
end

local exists = redis.call('EXISTS', key)
if exists == 0 then
    return -1
end

local stock = redis.call('HGET', key, 'quantity')
if not stock then
    return -1
end

local current_qty = tonumber(stock)
if current_qty < order_qty then
    return -2
end

local new_qty = current_qty - order_qty
redis.call('HSET', key, 'quantity', tostring(new_qty))
return new_qty
"""


def init_consumer_group(client: redis.client.Redis, key: str, group: str) -> None:
    """
    Initializes consumer group for Redis stream if it doesn't already exist.
    """
    try:
        client.xgroup_create(key, group, id="0", mkstream=True)
        logger.info(f"Consumer group '{group}' created for stream '{key}'.")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group '{group}' already exists for stream '{key}'.")
        else:
            logger.warning(f"Unexpected Redis ResponseError during group creation: {e}")
    except Exception as e:
        logger.warning(f"Failed to create consumer group '{group}': {e}")


async def process_order_message(
    redis_stream_client: redis.client.Redis,
    key: str,
    group: str,
    message_id: str,
    obj: dict,
) -> None:
    """
    Processes an individual order message atomically using a Redis Lua script.
    """
    try:
        product_id = obj.get("product_id")
        order_qty = int(obj.get("order_quantity", 0))

        redis_key = Product.make_primary_key(product_id)
        # Execute atomic Lua decrement via worker thread
        result = await asyncio.to_thread(
            redis_stream_client.eval,
            LUA_ATOMIC_DECREMENT,
            1,
            redis_key,
            order_qty,
        )

        if result == -1:
            logger.warning(
                f"⚠️ Product not found in inventory for ID: {product_id}. Triggering refund."
            )
            StreamService.stream_order_refund(obj)
            logger.success(f"Refund event streamed for order ID: {obj.get('order_id')}")
        elif result == -2:
            logger.warning(
                f"⚠️ Insufficient inventory for product {product_id}. "
                f"Requested: {order_qty}. Triggering refund."
            )
            StreamService.stream_order_refund(obj)
            logger.success(f"Refund event streamed for order ID: {obj.get('order_id')}")
        else:
            # Stock decremented atomically, clear caches
            await FastAPICache.clear(namespace="inventory.products")
            await clear_cache_by_pk(pk=product_id, namespace="inventory.product")
            logger.success(
                f"Decremented stock for product {product_id}. Remaining: {result}"
            )

        # Acknowledge the message so it's cleared from PEL
        await asyncio.to_thread(redis_stream_client.xack, key, group, message_id)

    except Exception as item_err:
        logger.exception(f"Error processing order message {message_id}: {item_err}")


async def recover_pel_inventory(
    redis_stream_client: redis.client.Redis,
    key: str,
    group: str,
    consumer: str,
    min_idle_time: int = 60000,
) -> None:
    """
    Recover unacknowledged messages from the Pending Entries List (PEL) on startup.
    Uses xautoclaim to claim and process messages idle for longer than min_idle_time ms.
    """
    logger.info(f"Checking for pending entries (PEL recovery) on stream '{key}' for group '{group}'...")
    start_id = "0-0"
    try:
        while True:
            claim_result = await asyncio.to_thread(
                redis_stream_client.xautoclaim,
                key,
                group,
                consumer,
                min_idle_time=min_idle_time,
                start_id=start_id,
                count=50,
            )
            if not claim_result:
                break

            next_start_id = claim_result[0]
            messages = claim_result[1]

            if not messages:
                break

            logger.info(f"PEL recovery: claimed {len(messages)} pending message(s) from stream '{key}'.")
            for message_id, obj in messages:
                if obj:
                    await process_order_message(redis_stream_client, key, group, message_id, obj)

            if next_start_id == "0-0" or next_start_id == start_id or not next_start_id:
                break
            start_id = next_start_id
    except Exception as e:
        logger.warning(f"PEL recovery check encountered: {e}")


async def consume_order_completed(
    redis_stream_client: redis.client.Redis,
    key: str = STREAM_KEY,
    group: str = CONSUMER_GROUP,
    consumer: str = CONSUMER_NAME,
    block_: int = 3000,
):
    """
    Continuously listens to the Redis stream for completed order events.
    Non-blocking event loop execution using asyncio.to_thread for synchronous Redis calls.
    """
    Product.set_meta_attr(redis_stream_client, global_key_prefix="inventory_order_system", model_key_prefix="inventory.Product")
    init_consumer_group(redis_stream_client, key, group)
    await recover_pel_inventory(redis_stream_client, key, group, consumer)

    while True:
        try:
            # Read new messages from Redis stream in a non-blocking thread
            messages = await asyncio.to_thread(
                redis_stream_client.xreadgroup,
                group,
                consumer,
                {key: ">"},
                count=10,
                block=block_,
            )

            if messages:
                for stream_name, message_list in messages:
                    for message_id, obj in message_list:
                        await process_order_message(redis_stream_client, key, group, message_id, obj)

        except Exception as e:
            logger.exception(f"Error consuming Redis stream: {e}")

        await asyncio.sleep(1)  # Prevent busy-waiting


async def consume():
    redis_stream_client = get_redis_om_client()
    redis_cache = get_redis_cache_client()
    FastAPICache.init(RedisBackend(redis_cache), prefix="fastapi-cache", coder=CustomJsonCoder)

    await consume_order_completed(redis_stream_client, STREAM_KEY, CONSUMER_GROUP)


if __name__ == "__main__":
    asyncio.run(consume())
