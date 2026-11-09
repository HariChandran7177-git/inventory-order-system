from typing import List

from fastapi import APIRouter, HTTPException

from payment.app.db.postgresql import SessionDep
from payment.app.models.models import Order, UpdateOrder
from payment.app.services.service import OrderService

# Note: This router is deprecated and pruned from the primary API surface in main.py.
# Direct creation of unvalidated orders has been disabled to prevent inventory bypass.
router = APIRouter(prefix="/CRUD/orders", tags=["CRUD-Orders (Deprecated)"], deprecated=True)


@router.post("/", response_model=Order)
async def create_order(order: Order, session: SessionDep):
    """
    Disabled endpoint: Prevents unvalidated orders from bypassing inventory and fee checks.
    """
    raise HTTPException(
        status_code=400,
        detail="Direct order creation via /CRUD/orders/ is disabled. Please use POST /orders/ to ensure inventory validation and stream processing.",
    )


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: int, session: SessionDep):
    """
    Retrieves an order by order_id.
    """
    order = await OrderService.get_order(order_id, session)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with id {order_id} not found")
    return order


@router.get("/", response_model=List[Order])
async def get_all_orders(session: SessionDep):
    """
    Retrieves all orders.
    """
    return await OrderService.get_all_orders(session)


@router.put("/{order_id}", response_model=Order)
async def update_order(order_id: int, updated_data: UpdateOrder, session: SessionDep):
    """
    Updates an existing order.
    """
    order = await OrderService.update_order(order_id, updated_data, session)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order with id {order_id} not found")
    return order


@router.delete("/{order_id}", response_model=dict)
async def delete_order(order_id: int, session: SessionDep):
    """
    Deletes an order.
    """
    deleted_order = await OrderService.delete_order(order_id, session)
    if not deleted_order:
        raise HTTPException(status_code=404, detail=f"Order with id {order_id} not found")
    return deleted_order
