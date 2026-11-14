/**
 * Centralized Inventory Order System API Client
 * Provides structured, resilient client services for both Inventory (port 8000)
 * and Payment (port 8001) microservices.
 */

const INVENTORY_BASE_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_INVENTORY_API_URL ||
  "http://localhost:8000"

const PAYMENT_BASE_URL =
  import.meta.env.VITE_PAYMENT_API_URL ||
  "http://localhost:8001"

/**
 * Generic fetch wrapper with robust JSON parsing and HTTP error handling.
 */
async function request(url, options = {}) {
  const config = {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  }

  let response
  try {
    response = await fetch(url, config)
  } catch (networkError) {
    throw new Error(`Network error connecting to ${url}: ${networkError.message}`)
  }

  // Parse JSON response body if available
  let data = null
  const contentType = response.headers.get("content-type")
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await response.json()
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    const errorDetail =
      (data && (data.detail || data.message || data.error)) ||
      `HTTP ${response.status}: ${response.statusText}`
    const error = new Error(errorDetail)
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

/**
 * Inventory Service Client (port 8000)
 */
export const inventoryApi = {
  baseUrl: INVENTORY_BASE_URL,

  async getHealth() {
    return request(`${INVENTORY_BASE_URL}/health`)
  },

  async getProducts(category) {
    const url = category ? `${INVENTORY_BASE_URL}/inventory/products?category=${encodeURIComponent(category)}` : `${INVENTORY_BASE_URL}/inventory/products`
    return request(url)
  },

  async getProduct(pk) {
    if (!pk) throw new Error("Product primary key (pk) is required")
    return request(`${INVENTORY_BASE_URL}/inventory/product/${pk}`)
  },

  async createProduct({ name, price, quantity, category }) {
    return request(`${INVENTORY_BASE_URL}/inventory/product`, {
      method: "POST",
      body: JSON.stringify({
        name: String(name).trim(),
        price: parseFloat(price),
        quantity: parseInt(quantity, 10),
        category: category ? String(category).trim() : undefined,
      }),
    })
  },

  async updateProduct(pk, { name, price, quantity, category }) {
    if (!pk) throw new Error("Product primary key (pk) is required for update")
    const payload = {}
    if (name !== undefined) payload.name = String(name).trim()
    if (price !== undefined) payload.price = parseFloat(price)
    if (quantity !== undefined) payload.quantity = parseInt(quantity, 10)
    if (category !== undefined) payload.category = String(category).trim()

    return request(`${INVENTORY_BASE_URL}/inventory/product/${pk}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    })
  },

  async deleteProduct(pk) {
    if (!pk) throw new Error("Product primary key (pk) is required for delete")
    return request(`${INVENTORY_BASE_URL}/inventory/product/${pk}`, {
      method: "DELETE",
    })
  },
}

/**
 * Payment Service Client (port 8001)
 */
export const paymentApi = {
  baseUrl: PAYMENT_BASE_URL,

  async getHealth() {
    return request(`${PAYMENT_BASE_URL}/health`)
  },

  async getOrders() {
    return request(`${PAYMENT_BASE_URL}/orders/`)
  },

  async validateCheckout(items) {
    if (!Array.isArray(items) || items.length === 0) {
      throw new Error("Validation requires a non-empty list of cart items")
    }

    const payload = {
      items: items.map(item => ({
        product_id: String(item.id || item.product_id).trim(),
        order_quantity: parseInt(item.quantity || item.order_quantity, 10),
        client_price: parseFloat(item.price || item.client_price || 0),
      })),
    }

    return request(`${PAYMENT_BASE_URL}/orders/validate`, {
      method: "POST",
      body: JSON.stringify(payload),
    })
  },

  async getOrder(orderId) {
    if (!orderId) throw new Error("Order ID is required")
    return request(`${PAYMENT_BASE_URL}/orders/${orderId}`)
  },

  async createOrder({ product_id, order_quantity }) {
    const qty = parseInt(order_quantity, 10)
    if (!product_id) throw new Error("product_id is required")
    if (isNaN(qty) || qty <= 0) {
      throw new Error("order_quantity must be an integer greater than 0")
    }

    return request(`${PAYMENT_BASE_URL}/orders/`, {
      method: "POST",
      body: JSON.stringify({
        product_id: String(product_id).trim(),
        order_quantity: qty,
      }),
    })
  },

  async updateOrder(orderId, updateData) {
    if (!orderId) throw new Error("Order ID is required")
    return request(`${PAYMENT_BASE_URL}/orders/${orderId}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    })
  },

  async deleteOrder(orderId) {
    if (!orderId) throw new Error("Order ID is required")
    return request(`${PAYMENT_BASE_URL}/orders/${orderId}`, {
      method: "DELETE",
    })
  },
}
