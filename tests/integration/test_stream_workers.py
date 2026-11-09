import pytest
from unittest.mock import patch, AsyncMock
from inventory.app.models.models import Product
from inventory.app.workers.consumer import process_order_message, init_consumer_group
from payment.app.workers.consumer import process_refund_message, init_consumer_group as init_payment_group
from payment.app.models.models import Order
from tests.conftest import MockAsyncSession


@pytest.mark.asyncio
async def test_inventory_worker_decrement_success(fake_redis):
    """
    Tier 3 / Tier 4: Verify inventory worker decrements stock atomically via Lua script and ACKs.
    """
    p = Product(name="Mechanical Switch Pack", price=25.0, quantity=30)
    p.save()

    # Initialize consumer group
    init_consumer_group(fake_redis, "order_completed", "inventory_group")

    msg_id = fake_redis.xadd("order_completed", {
        "product_id": p.pk,
        "order_quantity": "5",
        "order_id": "1001",
    })

    # Process message
    await process_order_message(
        redis_stream_client=fake_redis,
        key="order_completed",
        group="inventory_group",
        message_id=msg_id,
        obj={"product_id": p.pk, "order_quantity": "5", "order_id": "1001"},
    )

    # Verify stock decremented
    updated_p = Product.get(p.pk)
    assert updated_p.quantity == 25

    # Verify ACK was called (message cleared from PEL)
    pel = fake_redis.xpending("order_completed", "inventory_group")
    assert pel["pending"] == 0


@pytest.mark.asyncio
async def test_inventory_worker_insufficient_stock_triggers_refund(fake_redis):
    """
    Tier 3: When order requested quantity exceeds available stock, worker triggers refund_order event.
    """
    p = Product(name="Last Available Keyboard", price=150.0, quantity=2)
    p.save()

    init_consumer_group(fake_redis, "order_completed", "inventory_group")
    msg_id = fake_redis.xadd("order_completed", {
        "product_id": p.pk,
        "order_quantity": "5",
        "order_id": "1002",
    })

    with patch("inventory.app.services.stream_service.get_redis_stream_client", return_value=fake_redis):
        await process_order_message(
            redis_stream_client=fake_redis,
            key="order_completed",
            group="inventory_group",
            message_id=msg_id,
            obj={"product_id": p.pk, "order_quantity": "5", "order_id": "1002"},
        )

    # Stock should remain untouched
    updated_p = Product.get(p.pk)
    assert updated_p.quantity == 2

    # Refund stream should receive the event
    assert fake_redis.xlen("refund_order") == 1
    refund_msgs = fake_redis.xrange("refund_order")
    assert refund_msgs[0][1]["order_id"] == "1002"


@pytest.mark.asyncio
async def test_inventory_worker_missing_product_triggers_refund(fake_redis):
    """
    Tier 3: When order references a non-existent product, worker triggers refund_order event.
    """
    init_consumer_group(fake_redis, "order_completed", "inventory_group")
    msg_id = fake_redis.xadd("order_completed", {
        "product_id": "missing_prod_pk",
        "order_quantity": "1",
        "order_id": "1003",
    })

    with patch("inventory.app.services.stream_service.get_redis_stream_client", return_value=fake_redis):
        await process_order_message(
            redis_stream_client=fake_redis,
            key="order_completed",
            group="inventory_group",
            message_id=msg_id,
            obj={"product_id": "missing_prod_pk", "order_quantity": "1", "order_id": "1003"},
        )

    assert fake_redis.xlen("refund_order") == 1


@pytest.mark.asyncio
async def test_payment_worker_refund_status_update(fake_redis, mock_session: MockAsyncSession):
    """
    Tier 3: Verify payment worker consumes refund message and marks order 'refunded'.
    """
    order = Order(
        order_id=2001,
        product_id="prod_xyz",
        price=50.0,
        fee_per_unit=10.0,
        total=60.0,
        order_quantity=1,
        status="completed",
    )
    mock_session.orders[2001] = order

    init_payment_group(fake_redis, "refund_order", "payment_group")
    msg_id = fake_redis.xadd("refund_order", {"order_id": "2001", "status": "refunded"})

    # Patch AsyncSession in worker to use our mock_session
    class MockSessionContext:
        async def __aenter__(self):
            return mock_session
        async def __aexit__(self, *args):
            pass

    with patch("payment.app.workers.consumer.AsyncSession", return_value=MockSessionContext()):
        await process_refund_message(
            redis_stream_client=fake_redis,
            key="refund_order",
            group="payment_group",
            message_id=msg_id,
            obj={"order_id": "2001", "status": "refunded"},
        )

    assert mock_session.orders[2001].status == "refunded"
    # Verify ACK was called
    pel = fake_redis.xpending("refund_order", "payment_group")
    assert pel["pending"] == 0
