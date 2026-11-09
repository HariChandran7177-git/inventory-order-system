import asyncio

import redis
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from payment.app.db.postgresql import async_engine
from payment.app.db.redis_stream import get_redis_stream_client
from payment.app.services.service import OrderService

STREAM_KEY = "refund_order"
CONSUMER_GROUP = "payment_group"
CONSUMER_NAME = "payment_consumer_1"


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


async def process_refund_message(
    redis_stream_client: redis.client.Redis,
    key: str,
    group: str,
    message_id: str,
    obj: dict,
) -> None:
    """
    Processes an individual refund message and updates the order status in PostgreSQL.
    """
    try:
        order_id = int(obj.get("order_id", 0))
        async with AsyncSession(async_engine) as session:
            order = await OrderService.get_order(order_id, session)

            if order:
                logger.info(f"Fetched order from sql db: {order}")
                order.status = "refunded"
                await session.commit()
                await session.refresh(order)
                logger.success(f"Order with ID {order_id} refunded successfully.")
            else:
                logger.warning(f"Order with ID {order_id} not found in the database.")

        # Acknowledge the message to remove from PEL
        await asyncio.to_thread(redis_stream_client.xack, key, group, message_id)
    except Exception as msg_err:
        logger.exception(f"Error processing refund message {message_id}: {msg_err}")


async def recover_pel_refund(
    redis_stream_client: redis.client.Redis,
    key: str,
    group: str,
    consumer: str,
    min_idle_time: int = 60000,
) -> None:
    """
    Recover unacknowledged messages from the Pending Entries List (PEL) on startup.
    Uses xautoclaim to reclaim and process messages idle for longer than min_idle_time ms.
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

            logger.info(f"PEL recovery: claimed {len(messages)} pending refund message(s) from stream '{key}'.")
            for message_id, obj in messages:
                if obj:
                    await process_refund_message(redis_stream_client, key, group, message_id, obj)

            if next_start_id == "0-0" or next_start_id == start_id or not next_start_id:
                break
            start_id = next_start_id
    except Exception as e:
        logger.warning(f"PEL recovery check encountered: {e}")


async def consume_order_refund(
    redis_stream_client: redis.client.Redis,
    key: str = STREAM_KEY,
    group: str = CONSUMER_GROUP,
    consumer: str = CONSUMER_NAME,
    block_: int = 3000,
):
    """
    Continuously listens to the Redis stream for refund order events.
    Non-blocking event loop execution using asyncio.to_thread for synchronous Redis calls.
    """
    init_consumer_group(redis_stream_client, key, group)
    await recover_pel_refund(redis_stream_client, key, group, consumer)

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
                        await process_refund_message(redis_stream_client, key, group, message_id, obj)

        except Exception as e:
            logger.exception(f"Error consuming Redis stream: {e}")

        await asyncio.sleep(1)  # Prevent busy-waiting


async def consume():
    redis_stream_client = get_redis_stream_client()
    await consume_order_refund(redis_stream_client, STREAM_KEY, CONSUMER_GROUP)


if __name__ == "__main__":
    asyncio.run(consume())
