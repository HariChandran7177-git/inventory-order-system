# 🛒 Storefront & Administration Web Application

The **Frontend Application** is a modern, responsive Single Page Application (SPA) built with **React 19**, **Vite**, and **Bootstrap 5.3**. It provides a real-time shopping experience for customers and a full administrative dashboard for catalog management.

---

## ⚡ Technical Specifications

- **Port:** `3000`
- **Framework:** React 19 (`react` & `react-dom`)
- **Build Tool:** Vite 6.2
- **Routing:** React Router 7 (`BrowserRouter`, `Routes`, `Route`, `NavLink`)
- **Styling:** Bootstrap 5.3 + Bootstrap Icons (bundled locally via npm, zero runtime CDN dependency)
- **State Management:** React Context API (`CartContext`) with `localStorage` persistence
- **Resilience:** Global React `ErrorBoundary` component

---

## 📂 Folder Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.js             # Unified dual-service HTTP client (Port 8000 & 8001)
│   ├── components/
│   │   ├── CartDrawer.jsx        # Offcanvas cart drawer with tax & fee breakdown
│   │   ├── ErrorBoundary.jsx     # Global error catching component
│   │   ├── NotFound.jsx          # 404 handler with return home navigation
│   │   ├── Orders.jsx            # Order history, status badges & cancellations
│   │   ├── ProductEdit.jsx       # Admin product modification form
│   │   ├── products.jsx          # Admin inventory table with search & category badges
│   │   ├── products_create.jsx   # Admin new product creation form
│   │   ├── ProductsStore.jsx     # Customer storefront grid, category filters & quick view
│   │   └── wrapper.jsx           # Application shell, sticky navbar & cart trigger
│   ├── context/
│   │   └── CartContext.jsx       # Cart state, item quantities & price computation
│   ├── utils/
│   │   └── formatters.js         # Currency, date, and fee/tax calculations
│   ├── App.jsx                   # Central route configurations
│   ├── index.css                 # Custom styling overrides
│   └── main.jsx                  # React application entrypoint
├── package.json                  # Dependencies & scripts
└── vite.config.js                # Vite dev server configuration
```

---

## 🌟 Key Application Views

### 1. Customer Storefront (`/`)
- Live product grid with real-time stock badges (`In Stock (N)` vs `Out of Stock`).
- Category filter pills (`All Categories`, `Electronics`, `Home`, etc.) and dynamic search bar.
- Price preview showing main price (incl. 5% GST), ex-GST base price, and 1.5% platform fee badge.
- **Quick View Modal:** Displays complete itemized specifications and pricing breakdown.

### 2. Offcanvas Shopping Cart Drawer
- Slide-over drawer accessible from anywhere via the sticky header.
- Increment/decrement quantity controls clamped to available stock.
- Transparent price summary:
  - Base Price (excl. 5% GST)
  - Included 5% GST
  - Subtotal (incl. GST)
  - Platform Fee (1.5%)
  - Grand Total
- Checkout flow: Posts individual orders to Payment API, handles partial failures gracefully, and presents confirmed Order IDs.

### 3. Admin Inventory Management (`/admin`)
- Real-time catalog table displaying Primary Key, Product Name, Category, Unit Price, Stock, and Registered Timestamp.
- Instant search filter by name, category, or ID.
- Actions: **Add Product** (`/admin/create`), **Edit Product** (`/admin/edit/:id`), and **Delete Product** with confirmation.

### 4. Order Tracking & History (`/orders`)
- Chronological order ledger showing Order #, Product ID, Quantity, Unit Price, Platform Fee (1.5%), Total Amount, Status Badge (`Completed`, `Pending`, `Refunded`), and Placement Date.
- Cancel / Delete action button.

---

## 🛠️ State Management Architecture (`CartContext`)

Cart state is centralized in `CartContext.jsx` and synchronized with `localStorage`:
```javascript
const CART_STORAGE_KEY = "inventory_order_system_cart"
```
Cart totals update reactively whenever quantities change:
- `subtotalWithoutGst`: Sum of `calculatePriceWithoutGst(price) * qty`
- `includedGst`: Sum of `calculateGstAmount(price) * qty`
- `subtotal`: Sum of `price * qty` (inclusive of GST)
- `platformFee`: Calculated at `1.5%` of subtotal
- `grandTotal`: `subtotal + platformFee`

---

## 🚀 How to Run Locally

From the project root:

```powershell
# 1. Start Frontend Vite Server (Port 3000)
npm run dev:frontend

# 2. Production Build Check
npm run build:frontend

# 3. Code Quality & Linting
npm --workspace=frontend run lint
```

Open **http://localhost:3000** in your browser.

