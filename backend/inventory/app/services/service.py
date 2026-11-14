# from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from loguru import logger
from redis_om.model.model import NotFoundError

from inventory.app.exceptions.custom_exceptions import CustomNotFoundException
from inventory.app.models.models import Product, UpdateProduct
from inventory.app.services.utils import (
    clear_cache_by_namespace,
    clear_cache_by_pk,
    product_format,
    product_key_builder,
)


class Service:
    """
    Service class to handle inventory operations.
    """

    def __init__(self) -> None:
        """
        Initialize the Service.
        """
        logger.debug("Service initialized")

    @cache(namespace="inventory.products", expire=600)  # Cache for 10 mins
    async def get_all_products(self) -> list[dict[str, str | float | int]]:
        """
        Get all products from the database using pipelined batch loading
        to eliminate N+1 single-item roundtrips.
        """
        pks = list(Product.all_pks())
        if not pks:
            return []

        try:
            db = Product.db()
            pipe = db.pipeline()
            for pk in pks:
                pipe.hgetall(Product.make_primary_key(pk))
            raw_products = pipe.execute()

            products: list[dict[str, str | float | int]] = []
            for pk, data in zip(pks, raw_products):
                if not data:
                    continue
                try:
                    product = Product.from_redis(data)
                    products.append(
                        {
                            "id": product.pk or pk,
                            "name": product.name,
                            "price": float(product.price),
                            "quantity": int(product.quantity),
                            "category": getattr(product, "category", "Uncategorized"),
                            "creation_time": str(product.creation_time),
                        }
                    )
                except Exception:
                    products.append(
                        {
                            "id": data.get("pk", pk),
                            "name": str(data.get("name", "")),
                            "price": float(data.get("price", 0.0)),
                            "quantity": int(data.get("quantity", 0)),
                            "category": str(data.get("category", "Uncategorized")),
                            "creation_time": str(data.get("creation_time", "")),
                        }
                    )
            return products
        except Exception as e:
            logger.warning(f"Batch loading failed, falling back to individual fetches: {e}")
            return [result for pk in pks if isinstance((result := await product_format(pk)), dict)]

    async def get_products_by_category(self, category: str) -> list[dict[str, str | float | int]]:
        """Fetch products filtered by a given category."""
        # Simple implementation: fetch all then filter (could be optimized)
        all_products = await self.get_all_products()
        return [p for p in all_products if p.get("category") == category]

    async def add_product(self, product: Product) -> Product:
        """
        Add a product to the database.
        """
        logger.debug(product)

        # Save the actual product to Redis
        product.save()

        # Invalidate the products list cache
        await clear_cache_by_namespace(namespace="inventory.products")

        return product

    @cache(namespace="inventory.product", key_builder=product_key_builder, expire=600)  # Cache for 10 mins
    async def get_product_by_pk(self, pk: str) -> dict[str, str | float | int]:
        """
        Get a product by its primary key (pk).
        """
        result = await product_format(pk)
        if isinstance(result, dict):
            return result
        raise CustomNotFoundException(id=pk)

    async def update_product_by_pk(self, pk: str, update_product: UpdateProduct) -> Product:
        """
        Update a product by its primary key (pk).
        """
        try:
            product = Product.get(pk)
        except NotFoundError:
            raise CustomNotFoundException(id=pk)

        update_data = update_product.model_dump(exclude_unset=True)

        product.update(**update_data)
        product.save()

        # Invalidate cache
        await clear_cache_by_pk(pk=pk, namespace="inventory.product")
        await clear_cache_by_namespace(namespace="inventory.products")

        return product

    async def delete_product_by_pk(self, pk: str) -> dict[str, str | float | int]:
        """
        Delete a product by its primary key (pk).
        """
        try:
            product = Product.get(pk)
        except NotFoundError:
            raise CustomNotFoundException(id=pk)

        product_dict = product.model_dump()
        Product.delete(product.pk)

        # After deleting, clear the cache for this product and list
        await clear_cache_by_namespace(namespace="inventory.products")
        await clear_cache_by_pk(pk=pk, namespace="inventory.product")

        return product_dict
