/**
 * Reusable formatting and safe parsing helpers for Inventory Order System
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
 * Calculate the price without 5% GST (GST is included in main unitPrice).
 * Formula: unitPrice / (1 + 0.05)
 */
export function calculatePriceWithoutGst(unitPrice, gstRate = 0.05) {
  const price = typeof unitPrice === "number" ? unitPrice : parseFloat(unitPrice) || 0
  return Math.round((price / (1 + gstRate)) * 100) / 100
}

/**
 * Calculate the included 5% GST amount from the main price.
 */
export function calculateGstAmount(unitPrice, gstRate = 0.05) {
  const price = typeof unitPrice === "number" ? unitPrice : parseFloat(unitPrice) || 0
  const priceWithoutGst = calculatePriceWithoutGst(price, gstRate)
  return Math.round((price - priceWithoutGst) * 100) / 100
}

/**
 * Calculate the 1.5% platform fee matching backend logic.
 */
export function calculatePlatformFee(unitPrice, rate = 0.015) {
  const price = typeof unitPrice === "number" ? unitPrice : parseFloat(unitPrice) || 0
  return Math.round(price * rate * 100) / 100
}

/**
 * Alias for calculatePlatformFee to maintain backward compatibility.
 */
export function calculateFeePerUnit(unitPrice, rate = 0.015) {
  return calculatePlatformFee(unitPrice, rate)
}

/**
 * Calculate total for an order: (main_unit_price + 1.5% platform_fee) * quantity.
 */
export function calculateOrderTotal(unitPrice, quantity = 1, rate = 0.015) {
  const price = typeof unitPrice === "number" ? unitPrice : parseFloat(unitPrice) || 0
  const fee = calculatePlatformFee(price, rate)
  const qty = parseQuantity(quantity, 1)
  return Math.round((price + fee) * qty * 100) / 100
}
