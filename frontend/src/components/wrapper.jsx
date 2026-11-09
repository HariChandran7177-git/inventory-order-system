import { Link, NavLink } from "react-router-dom"
import { useCart } from "../context/CartContext"
import { CartDrawer } from "./CartDrawer"

export const Wrapper = ({ children }) => {
  const { totalItems, setIsCartOpen } = useCart()

  return (
    <div className="app-container d-flex flex-column min-vh-100">
      {/* Top Navbar */}
      <header className="navbar navbar-expand-lg navbar-dark bg-dark sticky-top shadow-sm px-3">
        <div className="container-fluid">
          {/* Brand Logo */}
          <Link className="navbar-brand text-white fw-bold me-4 d-flex align-items-center gap-2" to="/">
            <i className="bi bi-box-seam fs-4"></i>
            <span>Inventory Order System</span>
          </Link>

          {/* Mobile toggle button */}
          <button
            className="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarContent"
            aria-controls="navbarContent"
            aria-expanded="false"
            aria-label="Toggle navigation"
          >
            <span className="navbar-toggler-icon"></span>
          </button>

          {/* Navigation Links */}
          <div className="collapse navbar-collapse" id="navbarContent">
            <ul className="navbar-nav me-auto mb-2 mb-lg-0">
              <li className="nav-item">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) =>
                    `nav-link px-3 ${isActive ? "active text-white fw-semibold" : "text-light"}`
                  }
                >
                  <i className="bi bi-shop me-1"></i> Storefront
                </NavLink>
              </li>
              <li className="nav-item">
                <NavLink
                  to="/admin"
                  className={({ isActive }) =>
                    `nav-link px-3 ${isActive ? "active text-white fw-semibold" : "text-light"}`
                  }
                >
                  <i className="bi bi-boxes me-1"></i> Inventory
                </NavLink>
              </li>
              <li className="nav-item">
                <NavLink
                  to="/orders"
                  className={({ isActive }) =>
                    `nav-link px-3 ${isActive ? "active text-white fw-semibold" : "text-light"}`
                  }
                >
                  <i className="bi bi-receipt me-1"></i> Orders
                </NavLink>
              </li>
            </ul>

            {/* Right-aligned Actions */}
            <div className="d-flex align-items-center gap-2 mt-2 mt-lg-0">
              {/* Shopping Cart Trigger */}
              <button
                type="button"
                className="btn btn-outline-light position-relative d-flex align-items-center gap-2 px-3"
                onClick={() => setIsCartOpen(true)}
                title="View shopping cart"
                aria-label={`View shopping cart${totalItems > 0 ? `, ${totalItems} items` : ""}`}
              >
                <i className="bi bi-cart3 fs-5"></i>
                <span className="d-none d-sm-inline">Cart</span>
                {totalItems > 0 && (
                  <span className="badge rounded-pill bg-danger">
                    {totalItems}
                    <span className="visually-hidden">items in cart</span>
                  </span>
                )}
              </button>

            </div>
          </div>
        </div>
      </header>

      {/* Main App Content */}
      <main className="flex-grow-1 container-fluid py-4 px-md-5">
        {children}
      </main>

      {/* Cart Drawer Component */}
      <CartDrawer />

      {/* App Footer */}
      <footer className="footer-custom bg-dark text-white-50 py-3 mt-auto border-top border-secondary">
        <div className="container-fluid px-md-5 d-flex flex-column flex-sm-row justify-content-between align-items-center small">
          <div className="mb-2 mb-sm-0">
            &copy; 2026 Inventory Order System Microservices Platform &mdash; Port 8000 (Inventory) &amp; Port 8001 (Payment).
          </div>
          <div className="d-flex gap-3">
            <Link to="/" className="text-decoration-none text-white-50 hover-light">
              Storefront
            </Link>
            <Link to="/admin" className="text-decoration-none text-white-50 hover-light">
              Admin
            </Link>
            <Link to="/orders" className="text-decoration-none text-white-50 hover-light">
              Orders
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
