# 📦 Inventory Catalog Microservice

The **Inventory Microservice** is a high-performance catalog management and stock-governance engine. It provides sub-millisecond read latency using Redis OM HashModels and FastAPICache, and guarantees **zero race-condition overselling** using atomic Redis Lua scripts.

---

## ⚡ Technical Specifications

- **Port:** `8000`
- **Framework:** FastAPI (Modern asynchronous lifespan handlers)
- **Primary Database:** Redis (Redis OM HashModel)
- **Caching Layer:** `fastapi-cache2` with RedisBackend (600s TTL Cache-Aside)
- **Message Broker:** Redis Streams (`order_completed` consumer group)
- **Concurrency Control:** Atomic Lua Script (`LUA_ATOMIC_DECREMENT`)

---

## 📂 Folder Structure

```
backend/inventory/
├── app/
│   ├── db/
│   │   └── redis.py              # Redis OM connection, FastAPICache initialization & CustomJsonCoder
│   ├── exceptions/
│   │   └── exceptions.py         # Custom domain exceptions (ProductNotFound, ValidationError)
│   ├── models/
│   │   └── models.py             # Product Redis OM HashModel, CreateProduct & UpdateProduct schemas
│   ├── routes/
│   │   └── route.py              # Product CRUD HTTP routes & /health probe
│   ├── services/
│   │   ├── service.py            # Inventory business logic & cache invalidation
│   │   └── utils.py              # Formatting helpers
│   ├── workers/
│   │   └── consumer.py           # Stream consumer with atomic Lua decrement & PEL recovery
│   └── main.py                   # FastAPI application root & lifespan context
└── requirements.txt              # Pinned microservice dependencies
```

---

## 🛡️ Concurrency & Zero Overselling Guarantee

In traditional SQL architectures, high-concurrency flash sales suffer from race conditions:
1. Two customers read stock = `1` simultaneously.
2. Both order 1 unit.
3. Both writes succeed, setting stock = `0`, but 2 units were sold (overselling).

**How This Service Solves It:**
Stock decrements are executed inside Redis via an **atomic Lua script**:
```lua
local current = redis.call('HGET', KEYS[1], 'quantity')
if not current then
    return -2 -- Product not found
end
local stock = tonumber(current)
local requested = tonumber(ARGV[1])
if stock >= requested then
    redis.call('HSET', KEYS[1], 'quantity', stock - requested)
    return stock - requested -- Success: returns remaining stock
else
    return -1 -- Insufficient stock
end
```
Because Redis executes Lua scripts as a single atomic transaction on its single-threaded execution core, **no concurrent read or write can interleave during evaluation**.

---

## 🔄 Event-Driven Background Worker

The inventory background consumer (`inventory.app.workers.consumer`):
1. **Startup PEL Recovery:** Inspects the consumer group's Pending Entries List (PEL) via `XAUTOCLAIM` to process any events left unacknowledged by a previously crashed consumer.
2. **Stream Reading:** Continuously reads from the `order_completed` stream using `XREADGROUP`.
3. **Atomic Decrement:** Invokes `LUA_ATOMIC_DECREMENT` to update Redis stock.
4. **Compensation Trigger:** If stock is insufficient, it publishes a `refund_order` compensation event to Redis Streams so the Payment Service can refund the customer.
5. **Acknowledgement:** Calls `XACK` only after stock is safely updated.

---

## 📡 REST API Reference

| Method | Endpoint | Description | Cache Behavior |
| :---: | :--- | :--- | :--- |
| `GET` | `/health` | Service health check | No cache |
| `GET` | `/inventory/products` | Retrieve all catalog products | 600s TTL (`inventory.products`) |
| `GET` | `/inventory/product/{pk}` | Retrieve single product by PK | 600s TTL (`inventory.product:{pk}`) |
| `POST` | `/inventory/product` | Add a new product with category | Invalidates `inventory.products` |
| `PUT` | `/inventory/product/{pk}` | Update name, price, stock, category | Invalidates item & list cache |
| `DELETE` | `/inventory/product/{pk}` | Delete product from catalog | Invalidates item & list cache |

---

## 🚀 How to Run Locally

From the project root:

```powershell
# 1. Start Inventory API (Port 8000 with auto-reload)
npm run dev:inventory

# 2. Start Background Stream Consumer (Optional)
npm run dev:inventory-worker
```

*Interactive Swagger UI:* [http://localhost:8000/docs](http://localhost:8000/docs)

