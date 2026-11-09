import asyncio

from loguru import logger
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from payment.app.db.postgresql import async_engine
from payment.app.models.models import Order
from payment.app.services.stream_service import StreamService


class ProcessService:

    @staticmethod
    async def process_order(order_id: int):
        """
        Processes an order by updating its status to 'completed'.

        Args:
            order_id (int): ID of the order to be processed.
        """
        await asyncio.sleep(5)  # Simulate processing time

        async with AsyncSession(async_engine) as session:
            statement = select(Order).where(Order.order_id == order_id)
            result = await session.exec(statement)
            fetched_new_order = result.first()

            if not fetched_new_order:
                logger.error(
                    f"Order with id {order_id} not found during processing")
                return

            fetched_new_order.status = "completed"
            await session.commit()
            await session.refresh(fetched_new_order)

            # * redis stream
            StreamService.stream_order_completed(fetched_new_order)
            logger.info(
                f"Order {order_id} marked as completed and streamed to Redis")
