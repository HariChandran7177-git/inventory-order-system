/**
 * Reusable formatting and safe parsing helpers for Fast Cart
 */

/**
 * Safely format a price to a currency string ($XX.XX).
 * Handles numbers, numeric strings, null, undefined, and NaN gracefully.
 */
export function formatPrice(value, fallback = "$0.00") {
  if (value === null || value === undefined || value === "") {
    return fallback
  }
  const num = typeof value === "number" ? value : parseFloat(value)
  if (isNaN(num)) {
    return fallback
  }
  return `$${num.toFixed(2)}`
}

/**
 * Safely format a date/timestamp to a localized string.
 * Handles ISO strings, timestamps, null, undefined, and invalid dates gracefully.
 */
export function formatDate(dateValue, fallback = "N/A") {
  if (!dateValue) {
    return fallback
  }
  try {
    const d = new Date(dateValue)
    if (isNaN(d.getTime())) {
      return fallback
    }
    return d.toLocaleString("en-US", {
      month: "short",
      day: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    })
  } catch {
    return fallback
  }
}

/**
 * Safely parse quantity to non-negative integer.
 */
export function parseQuantity(value, defaultValue = 0) {
  if (value === null || value === undefined) return defaultValue
  const parsed = parseInt(value, 10)
  return isNaN(parsed) || parsed < 0 ? defaultValue : parsed
}

/**
 * Calculate the exact fee matching backend logic (20% fee rounded to 2 decimal places).
 */
export function calculateFeePerUnit(unitPrice, rate = 0.2) {
  const price = typeof unitPrice === "number" ? unitPrice : parseFloat(unitPrice) || 0
  return Math.round(price * rate * 100) / 100
}

/**
 * Calculate total for an order (unit_price + fee_per_unit) * quantity.
 */
export function calculateOrderTotal(unitPrice, quantity = 1, rate = 0.2) {
  const price = typeof unitPrice === "number" ? unitPrice : parseFloat(unitPrice) || 0
  const fee = calculateFeePerUnit(price, rate)
  const qty = parseQuantity(quantity, 1)
  return Math.round((price + fee) * qty * 100) / 100
}
