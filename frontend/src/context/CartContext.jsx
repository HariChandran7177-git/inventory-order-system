import { createContext, useContext, useEffect, useState } from "react"
import {
  calculateGstAmount,
  calculatePlatformFee,
  calculatePriceWithoutGst,
  parseQuantity,
} from "../utils/formatters"

const CartContext = createContext(null)

const CART_STORAGE_KEY = "inventory_order_system_cart"

export const CartProvider = ({ children }) => {
  const [cartItems, setCartItems] = useState(() => {
    try {
      const saved = localStorage.getItem(CART_STORAGE_KEY)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })

  const [isCartOpen, setIsCartOpen] = useState(false)

  // Sync cart items to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cartItems))
    } catch (e) {
      console.warn("Failed to persist cart items to localStorage", e)
    }
  }, [cartItems])

  const addToCart = (product, quantity = 1) => {
    const qtyToAdd = parseQuantity(quantity, 1)
    if (qtyToAdd <= 0) return

    setCartItems(prev => {
      const existingIndex = prev.findIndex(item => item.id === product.id)
      const availableStock = parseQuantity(product.quantity, 0)

      if (existingIndex > -1) {
        const existing = prev[existingIndex]
        const newQty = Math.min(existing.quantity + qtyToAdd, availableStock)
        const updated = [...prev]
        updated[existingIndex] = {
          ...existing,
          quantity: newQty,
          availableStock,
        }
        return updated
      } else {
        const initialQty = Math.min(qtyToAdd, availableStock)
        return [
          ...prev,
          {
            id: product.id,
            name: product.name,
            price: parseFloat(product.price) || 0,
            quantity: initialQty,
            availableStock,
          },
        ]
      }
    })
  }

  const updateQuantity = (productId, newQuantity) => {
    const qty = parseInt(newQuantity, 10)
    setCartItems(prev => {
      if (isNaN(qty) || qty <= 0) {
        return prev.filter(item => item.id !== productId)
      }
      return prev.map(item => {
        if (item.id === productId) {
          const clamped = Math.min(qty, item.availableStock || 9999)
          return { ...item, quantity: clamped }
        }
        return item
      })
    })
  }

  const removeFromCart = productId => {
    setCartItems(prev => prev.filter(item => item.id !== productId))
  }

  const clearCart = () => {
    setCartItems([])
  }

  const totalItems = cartItems.reduce((sum, item) => sum + item.quantity, 0)

  // Subtotal in main prices (which include 5% GST)
  const subtotal = cartItems.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  )

  // Subtotal without 5% GST
  const subtotalWithoutGst = cartItems.reduce(
    (sum, item) => sum + calculatePriceWithoutGst(item.price) * item.quantity,
    0
  )

  // 5% GST amount included in the main price
  const includedGst = cartItems.reduce(
    (sum, item) => sum + calculateGstAmount(item.price) * item.quantity,
    0
  )

  // 1.5% platform fee added at checkout
  const platformFee = cartItems.reduce(
    (sum, item) => sum + calculatePlatformFee(item.price) * item.quantity,
    0
  )

  const grandTotal = subtotal + platformFee

  return (
    <CartContext.Provider
      value={{
        cartItems,
        isCartOpen,
        setIsCartOpen,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        totalItems,
        subtotal,
        subtotalWithoutGst,
        includedGst,
        platformFee,
        estimatedFee: platformFee, // backward-compatibility
        grandTotal,
      }}
    >
      {children}
    </CartContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useCart = () => {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error("useCart must be used within a CartProvider")
  }
  return context
}
