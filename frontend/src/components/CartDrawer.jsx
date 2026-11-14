import { useNavigate } from "react-router-dom"
import { useCart } from "../context/CartContext"
import { formatPrice } from "../utils/formatters"

export const CartDrawer = () => {
  const {
    cartItems,
    isCartOpen,
    setIsCartOpen,
    updateQuantity,
    removeFromCart,
    subtotal,
    subtotalWithoutGst,
    includedGst,
    platformFee,
    grandTotal,
  } = useCart()

  const navigate = useNavigate()

  if (!isCartOpen) return null

  const handleClose = () => {
    setIsCartOpen(false)
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="modal-backdrop fade show"
        style={{ zIndex: 1040 }}
        onClick={handleClose}
      ></div>

      {/* Offcanvas Drawer */}
      <div
        className="offcanvas offcanvas-end show cart-drawer d-flex flex-column shadow-lg"
        tabIndex="-1"
        style={{
          zIndex: 1045,
          visibility: "visible",
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "#fff",
        }}
      >
        <div className="offcanvas-header border-bottom p-3">
          <h5 className="offcanvas-title d-flex align-items-center gap-2">
            <i className="bi bi-cart3 text-primary"></i> Shopping Cart
          </h5>
          <button
            type="button"
            className="btn-close"
            aria-label="Close"
            onClick={handleClose}
          ></button>
        </div>

        <div className="offcanvas-body flex-grow-1 p-3" style={{ overflowY: "auto" }}>
          {cartItems.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <i className="bi bi-cart-x display-4 text-secondary mb-3 d-block"></i>
              <h5>Your cart is currently empty</h5>
              <p className="small">Browse products in the storefront and add items to your cart.</p>
              <button
                type="button"
                className="btn btn-sm btn-outline-primary mt-2"
                onClick={handleClose}
              >
                Browse Products
              </button>
            </div>
          ) : (
            <div className="cart-item-list">
              {cartItems.map(item => (
                <div key={item.id} className="cart-item-row py-2">
                  <div className="d-flex justify-content-between align-items-start mb-1">
                    <span className="fw-semibold text-truncate me-2" style={{ maxWidth: "240px" }}>
                      {item.name}
                    </span>
                    <button
                      type="button"
                      className="btn btn-link text-danger p-0 border-0"
                      title="Remove item"
                      onClick={() => removeFromCart(item.id)}
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                  <div className="d-flex justify-content-between align-items-center small text-muted">
                    <span>{formatPrice(item.price)} each</span>
                    <span className="fw-bold text-dark">
                      {formatPrice(item.price * item.quantity)}
                    </span>
                  </div>
                  <div className="d-flex align-items-center gap-2 mt-2">
                    <div className="input-group input-group-sm" style={{ width: "110px" }}>
                      <button
                        className="btn btn-outline-secondary"
                        type="button"
                        onClick={() => updateQuantity(item.id, item.quantity - 1)}
                        disabled={item.quantity <= 1}
                      >
                        -
                      </button>
                      <span className="form-control text-center py-1 px-2">
                        {item.quantity}
                      </span>
                      <button
                        className="btn btn-outline-secondary"
                        type="button"
                        onClick={() => updateQuantity(item.id, item.quantity + 1)}
                        disabled={item.availableStock && item.quantity >= item.availableStock}
                      >
                        +
                      </button>
                    </div>
                    {item.availableStock && (
                      <span className="small text-muted">
                        (max {item.availableStock})
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {cartItems.length > 0 && (
          <div className="border-top p-3 bg-light">
            <div className="d-flex justify-content-between small text-muted mb-1">
              <span>Price (excl. 5% GST)</span>
              <span>{formatPrice(subtotalWithoutGst)}</span>
            </div>
            <div className="d-flex justify-content-between small text-muted mb-1">
              <span>Included 5% GST</span>
              <span className="text-secondary">{formatPrice(includedGst)}</span>
            </div>
            <div className="d-flex justify-content-between small fw-semibold text-dark mb-1 pt-1 border-top">
              <span>Main Price (incl. GST)</span>
              <span>{formatPrice(subtotal)}</span>
            </div>
            <div className="d-flex justify-content-between small text-muted mb-2">
              <span>Platform Fee (1.5%)</span>
              <span>{formatPrice(platformFee)}</span>
            </div>
            <div className="d-flex justify-content-between fw-bold fs-5 border-top pt-2 mb-3">
              <span>Total Price</span>
              <span className="text-primary">{formatPrice(grandTotal)}</span>
            </div>
            <button
              type="button"
              className="btn btn-primary w-100 py-2 fw-semibold d-flex align-items-center justify-content-center gap-2"
              onClick={() => {
                handleClose()
                navigate("/checkout")
              }}
            >
              <i className="bi bi-shield-check"></i> Proceed to Checkout &amp; Pay
            </button>
          </div>
        )}
      </div>
    </>
  )
}
