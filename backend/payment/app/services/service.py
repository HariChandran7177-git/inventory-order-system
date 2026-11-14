import os

import httpx
from fastapi import HTTPException
from loguru import logger
from sqlalchemy import update
from sqlmodel import select

from payment.app.db.postgresql import SessionDep
from payment.app.models.models import Order, OrderRequest, UpdateOrder

INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")


class OrderService:
    """
    Handles Order business logic.
    """

    @staticmethod
    async def order_request(order_req: OrderRequest, session: SessionDep) -> Order:
        """
        Creates a new order request, validates with Inventory Service, and persists it in the database.

        Args:
            order_req (OrderRequest): An object containing the details of the order request.
            session (SessionDep): The database session dependency for interacting with the database.

        Returns:
            Order: The created Order object with details such as product ID, price, fee, total,
                   quantity, and status.

        Raises:
            HTTPException: If validation fails or inventory service is unreachable.
        """
        order_req_dict = order_req.model_dump()
        product_url = f"{INVENTORY_SERVICE_URL}/inventory/product/{order_req_dict['product_id']}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(product_url)
        except httpx.RequestError as exc:
            logger.error(f"Failed to reach inventory service at {product_url}: {exc}")
            raise HTTPException(
                status_code=502,
                detail=f"Unable to connect to inventory service at {INVENTORY_SERVICE_URL}",
            )

        if res.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Product with id '{order_req_dict['product_id']}' not found in inventory.",
            )
        elif res.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Inventory service returned status code {res.status_code}",
            )

        product = res.json()
        if "quantity" not in product or "price" not in product:
            raise HTTPException(
                status_code=502,
                detail="Invalid response schema received from inventory service.",
            )

        # Validate order quantity against product quantity
        if int(order_req_dict["order_quantity"]) > int(product["quantity"]):
            raise HTTPException(
                status_code=400,
                detail=f"Requested quantity ({order_req_dict['order_quantity']}) exceeds available stock ({product['quantity']}).",
            )

        unit_price = round(float(product["price"]), 2)
        # 1.5% platform fee (unit_price is inclusive of 5% GST)
        fee_per_unit = round(0.015 * unit_price, 2)
        total = round((unit_price + fee_per_unit) * int(order_req_dict["order_quantity"]), 2)

        order = Order(
            product_id=str(product.get("id", order_req_dict["product_id"])),
            price=unit_price,
            fee_per_unit=fee_per_unit,
            total=total,
            order_quantity=int(order_req_dict["order_quantity"]),
            status="pending",
        )

        return await OrderService.create_order(order, session)

    @staticmethod
    async def create_order(order: Order, session: SessionDep) -> Order:
        """
        Creates a new order in the database.

        Args:
            order (Order): Order object to be added.
            session (Session): Database session.

        Returns:
            Order: The newly created order.
        """
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def get_order(order_id: int, session: SessionDep) -> Order | None:
        """
        Retrieves an order by order_id.

        Args:
            order_id (int): ID of the order.
            session (Session): Database session.

        Returns:
            Order | None: Found order or None.
        """
        return await session.get(Order, order_id)

    @staticmethod
    async def get_all_orders(session: SessionDep) -> list[Order]:
        """
        Retrieves all orders from the database.

        Args:
            session (Session): Database session.

        Returns:
            list[Order]: List of all orders.
        """
        return list((await session.exec(select(Order))).all())

    @staticmethod
    async def update_order(order_id: int, updated_data: UpdateOrder, session: SessionDep) -> Order | None:
        """
        Updates an order with new data using an optimized atomic `update().returning()` statement.

        Args:
            order_id (int): ID of the order to update.
            updated_data (UpdateOrder): Updated order data.
            session (SessionDep): Database session.

        Returns:
            Order | None: The updated order, or None if the order with the given order_id was not found.
        """
        update_data = updated_data.model_dump(exclude_unset=True)
        if not update_data:
            existing_order = await session.get(Order, order_id)
            if not existing_order:
                return None
            return existing_order

        # Run direct atomic update query with returning(Order) to avoid redundant select queries
        stmt = (
            update(Order)
            .where(Order.order_id == order_id)
            .values(**update_data)
            .returning(Order)
        )
        result = await session.execute(stmt)
        updated_order = result.scalars().first()

        if updated_order is None:
            return None

        await session.commit()
        return updated_order

    @staticmethod
    async def delete_order(order_id: int, session: SessionDep) -> dict | None:
        """
        Deletes an order by order_id.

        Args:
            order_id (int): ID of the order to delete.
            session (Session): Database session.

        Returns:
            dict: order dict if found and deleted successfully, None otherwise.
        """
        order = await session.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order with id {order_id} not found")

        order_dict = order.model_dump()
        await session.delete(order)
        await session.commit()
        return order_dict
