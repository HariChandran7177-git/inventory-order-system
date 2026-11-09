import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { ErrorBoundary } from "./components/ErrorBoundary"
import { CartProvider } from "./context/CartContext"
import { ProductsStore } from "./components/ProductsStore"
import { Products } from "./components/products"
import { ProductsCreate } from "./components/products_create"
import { ProductEdit } from "./components/ProductEdit"
import { Orders } from "./components/Orders"
import { NotFound } from "./components/NotFound"

function App() {
  return (
    <ErrorBoundary>
      <CartProvider>
        <BrowserRouter>
          <Routes>
            {/* Customer Storefront */}
            <Route path="/" element={<ProductsStore />} />

            {/* Admin Inventory Management */}
            <Route path="/admin" element={<Products />} />
            <Route path="/admin/create" element={<ProductsCreate />} />
            <Route path="/admin/edit/:id" element={<ProductEdit />} />

            {/* Legacy redirect for /create */}
            <Route path="/create" element={<Navigate to="/admin/create" replace />} />

            {/* Order Tracking & History */}
            <Route path="/orders" element={<Orders />} />

            {/* Catch-all 404 Route */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </CartProvider>
    </ErrorBoundary>
  )
}

export default App
