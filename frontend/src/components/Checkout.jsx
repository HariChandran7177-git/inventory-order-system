import { useState, useId } from "react"
import { Link } from "react-router-dom"
import { Wrapper } from "./wrapper"
import { useCart } from "../context/CartContext"
import { paymentApi } from "../api/client"
import { formatPrice } from "../utils/formatters"

export const Checkout = () => {
  const {
    cartItems,
    clearCart,
    removeFromCart,
    updateQuantity,
    syncCartItem,
    subtotal,
    subtotalWithoutGst,
    includedGst,
    platformFee,
    grandTotal,
  } = useCart()

  const nameId = useId()
  const emailId = useId()
  const addressId = useId()
  const cityId = useId()
  const zipId = useId()
  const cardNumId = useId()
  const cardExpId = useId()
  const cardCvvId = useId()
  const upiId = useId()

  // 2-Step Checkout Wizard: 1 = Review & Validation, 2 = Payment & Confirmation
  const [currentStep, setCurrentStep] = useState(1)

  // Customer shipping details
  const [customer, setCustomer] = useState({
    name: "John Doe",
    email: "john.doe@example.com",
    address: "123 Tech Boulevard",
    city: "San Francisco",
    zip: "94107",
  })

  // Payment details
  const [paymentMethod, setPaymentMethod] = useState("card") // 'card' | 'upi' | 'cod'
  const [cardDetails, setCardDetails] = useState({
    number: "4532 •••• •••• 8821",
    expiry: "09/28",
    cvv: "•••",
  })
  const [upiAddress, setUpiAddress] = useState("john@okhdfcbank")

  // Validation state (between Step 1 and Step 2)
  const [validating, setValidating] = useState(false)
  const [validationError, setValidationError] = useState(null)
  const [validationData, setValidationData] = useState(null)
  const [priceChangesPending, setPriceChangesPending] = useState(false)

  // Final order submission state
  const [submittingPayment, setSubmittingPayment] = useState(false)
  const [paymentError, setPaymentError] = useState(null)
  const [completedOrders, setCompletedOrders] = useState(null)

  /**
   * Transition Gate between Page 1 and Page 2:
   * Re-validates live stock and detects price hikes or drops.
   */
  const handleProceedToPayment = async () => {
    if (cartItems.length === 0) return

    setValidating(true)
    setValidationError(null)
    setValidationData(null)
    setPriceChangesPending(false)

    try {
      const result = await paymentApi.validateCheckout(cartItems)
      setValidationData(result)

      // Sync any updated stock or price back to cart state
      result.items.forEach(item => {
        syncCartItem(item.product_id, {
          price: item.current_price,
          availableStock: item.available_stock,
        })
      })

      if (result.has_stock_issues) {
        // Stock issue detected: cannot proceed to payment until resolved
        setValidationError(
          "One or more products in your cart have insufficient stock or are sold out. Please adjust quantities or remove out-of-stock items before proceeding."
        )
        return
      }

      if (result.has_price_changes) {
        // Price change detected (hike or drop): user must acknowledge
        setPriceChangesPending(true)
        return
      }

      // If 100% valid with no stock issues or price changes, advance directly to Step 2
      setCurrentStep(2)
    } catch (err) {
      console.error("Checkout validation failed:", err)
      setValidationError(
        err.message || "Failed to validate cart with live Inventory Service. Please try again."
      )
    } finally {
      setValidating(false)
    }
  }

  /**
   * User acknowledges price changes and proceeds to Step 2.
   */
  const handleAcceptPriceChanges = () => {
    setPriceChangesPending(false)
    setValidationError(null)
    setCurrentStep(2)
  }

  /**
   * Step 2: Final Payment Execution
   */
  const handleFinalPayment = async () => {
    setSubmittingPayment(true)
    setPaymentError(null)

    const created = []
    const errors = []

    for (const item of cartItems) {
      try {
        const order = await paymentApi.createOrder({
          product_id: item.id,
          order_quantity: item.quantity,
        })
        created.push(order)
      } catch (err) {
        errors.push(`${item.name}: ${err.message}`)
      }
    }

    setSubmittingPayment(false)

    if (errors.length > 0) {
      setPaymentError(errors.join(" | "))
      if (created.length > 0) {
        // Remove successfully created items
        created.forEach(o => removeFromCart(o.product_id))
      }
    } else {
      clearCart()
      setCompletedOrders(created)
    }
  }

  return (
    <Wrapper>
      <div className="container py-2" style={{ maxWidth: "1050px" }}>
        {/* Header Breadcrumb / Step Indicator */}
        <div className="mb-4 text-center">
          <h2 className="fw-bold mb-3">
            <i className="bi bi-shield-check text-primary me-2"></i> Two-Step Secure Checkout
          </h2>
          <div className="d-flex justify-content-center align-items-center gap-3">
            <span
              className={`badge rounded-pill px-3 py-2 fs-6 ${
                currentStep === 1 ? "bg-primary text-white" : "bg-success text-white"
              }`}
            >
              1. Review &amp; Stock Check {currentStep > 1 && <i className="bi bi-check-lg ms-1"></i>}
            </span>
            <i className="bi bi-arrow-right text-muted fs-5"></i>
            <span
              className={`badge rounded-pill px-3 py-2 fs-6 ${
                currentStep === 2 ? "bg-primary text-white" : "bg-light text-secondary border"
              }`}
            >
              2. Payment &amp; Confirmation
            </span>
          </div>
        </div>

        {/* Global Success Screen */}
        {completedOrders ? (
          <div className="card shadow-sm border-0 p-5 text-center my-4">
            <div className="text-success mb-3">
              <i className="bi bi-patch-check-fill display-2"></i>
            </div>
            <h3 className="fw-bold mb-2">Payment Completed &amp; Orders Registered!</h3>
            <p className="text-muted mb-4">
              Your payment has been accepted and order events have been published to the event bus.
            </p>
            <div className="bg-light p-4 rounded-3 text-start mx-auto mb-4" style={{ maxWidth: "600px" }}>
              <h6 className="fw-bold mb-3">
                <i className="bi bi-receipt me-2"></i>Confirmed Orders:
              </h6>
              <div className="list-group list-group-flush">
                {completedOrders.map(order => (
                  <div
                    key={order.order_id}
                    className="list-group-item bg-transparent d-flex justify-content-between align-items-center px-0 py-2"
                  >
                    <div>
                      <span className="fw-bold text-dark">Order #{order.order_id}</span>
                      <span className="text-muted small ms-2">({order.order_quantity} unit(s))</span>
                    </div>
                    <div>
                      <span className="badge bg-success me-2">{order.status}</span>
                      <span className="fw-bold text-primary">{formatPrice(order.total)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="d-flex justify-content-center gap-3">
              <Link to="/orders" className="btn btn-primary px-4 py-2">
                <i className="bi bi-receipt me-1"></i> View Order History
              </Link>
              <Link to="/" className="btn btn-outline-secondary px-4 py-2">
                Continue Shopping
              </Link>
            </div>
          </div>
        ) : cartItems.length === 0 ? (
          <div className="card shadow-sm border-0 p-5 text-center my-4">
            <i className="bi bi-cart-x display-3 text-muted mb-3 d-block"></i>
            <h4>Your Cart is Empty</h4>
            <p className="text-muted">There are no items to checkout.</p>
            <Link to="/" className="btn btn-primary mt-2 mx-auto" style={{ maxWidth: "200px" }}>
              Browse Storefront
            </Link>
          </div>
        ) : (
          <div className="row g-4">
            {/* Left Column: Form & Step Content */}
            <div className="col-12 col-lg-8">
              {/* PAGE 1: Order Review & Stock / Price Validation */}
              {currentStep === 1 && (
                <div className="card shadow-sm border-0 p-4 mb-4">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="fw-bold mb-0">
                      <i className="bi bi-bag-check me-2 text-primary"></i>Step 1: Order Review &amp; Validation
                    </h5>
                    <span className="badge bg-light text-dark border">
                      {cartItems.length} Product{cartItems.length > 1 ? "s" : ""}
                    </span>
                  </div>
                  <p className="text-muted small mb-4">
                    Review your items and shipping destination. When you proceed, the system will
                    verify live inventory stock and detect any catalog price updates.
                  </p>

                  {/* Validation Error Banner */}
                  {validationError && (
                    <div className="alert alert-danger d-flex align-items-start gap-2 mb-4" role="alert">
                      <i className="bi bi-exclamation-triangle-fill fs-5 mt-1 flex-shrink-0"></i>
                      <div className="flex-grow-1">
                        <strong>Inventory Validation Alert:</strong>
                        <p className="mb-0 small">{validationError}</p>
                      </div>
                    </div>
                  )}

                  {/* Price Fluctuations Banner (Price Hike or Drop) */}
                  {priceChangesPending && validationData?.has_price_changes && (
                    <div className="alert alert-warning border-warning shadow-sm mb-4 p-3" role="alert">
                      <div className="d-flex align-items-center gap-2 mb-2">
                        <i className="bi bi-graph-up-arrow fs-5 text-warning flex-shrink-0"></i>
                        <h6 className="fw-bold mb-0 text-dark">Price Update Detected in Catalog</h6>
                      </div>
                      <p className="small mb-3 text-secondary">
                        One or more item prices have changed in the live catalog since you added them to
                        your cart. Please review the changes:
                      </p>
                      <div className="bg-white p-2 rounded border mb-3">
                        {validationData.items
                          .filter(i => i.price_change_type !== "none")
                          .map(i => {
                            const isHike = i.price_change_type === "hike"
                            return (
                              <div
                                key={i.product_id}
                                className="d-flex justify-content-between align-items-center py-1 px-2 border-bottom last-border-0"
                              >
                                <span className="fw-semibold small">{i.name}</span>
                                <div className="text-end small">
                                  <span className="text-decoration-line-through text-muted me-2">
                                    {formatPrice(i.client_price)}
                                  </span>
                                  <span className={`fw-bold ${isHike ? "text-danger" : "text-success"}`}>
                                    {formatPrice(i.current_price)}
                                  </span>
                                  <span className={`badge ms-2 ${isHike ? "bg-danger" : "bg-success"}`}>
                                    {isHike ? `+${formatPrice(i.price_difference)} Hike` : `${formatPrice(i.price_difference)} Drop`}
                                  </span>
                                </div>
                              </div>
                            )
                          })}
                      </div>
                      <div className="d-flex justify-content-end gap-2">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => setPriceChangesPending(false)}
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm btn-warning fw-semibold"
                          onClick={handleAcceptPriceChanges}
                        >
                          <i className="bi bi-check-circle me-1"></i> Accept Updated Prices &amp; Proceed to Payment
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Items List Table */}
                  <div className="table-responsive mb-4">
                    <table className="table table-sm align-middle mb-0">
                      <thead className="table-light small">
                        <tr>
                          <th>Item</th>
                          <th className="text-center">Quantity</th>
                          <th className="text-end">Unit Price</th>
                          <th className="text-end">Total</th>
                          <th className="text-center">Stock Status</th>
                          <th className="text-center">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cartItems.map(item => {
                          const valItem = validationData?.items.find(
                            i => i.product_id === item.id
                          )
                          const hasStockIssue = valItem && !valItem.has_sufficient_stock
                          const hasPriceHike = valItem && valItem.price_change_type === "hike"
                          const hasPriceDrop = valItem && valItem.price_change_type === "drop"

                          return (
                            <tr
                              key={item.id}
                              className={
                                hasStockIssue
                                  ? "table-danger"
                                  : hasPriceHike
                                  ? "table-warning"
                                  : hasPriceDrop
                                  ? "table-success"
                                  : ""
                              }
                            >
                              <td>
                                <div className="fw-semibold text-dark">{item.name}</div>
                                <span className="font-monospace small text-muted">
                                  ID: {item.id.slice(0, 10)}...
                                </span>
                                {hasStockIssue && (
                                  <div className="small text-danger fw-bold mt-1">
                                    <i className="bi bi-exclamation-circle me-1"></i>
                                    Only {valItem.available_stock} in stock (requested {item.quantity})
                                  </div>
                                )}
                              </td>
                              <td className="text-center">
                                <div className="input-group input-group-sm mx-auto" style={{ width: "95px" }}>
                                  <button
                                    type="button"
                                    className="btn btn-outline-secondary"
                                    onClick={() => updateQuantity(item.id, item.quantity - 1)}
                                    disabled={item.quantity <= 1}
                                  >
                                    -
                                  </button>
                                  <span className="form-control text-center py-1 px-1">
                                    {item.quantity}
                                  </span>
                                  <button
                                    type="button"
                                    className="btn btn-outline-secondary"
                                    onClick={() => updateQuantity(item.id, item.quantity + 1)}
                                    disabled={valItem ? item.quantity >= valItem.available_stock : false}
                                  >
                                    +
                                  </button>
                                </div>
                              </td>
                              <td className="text-end text-muted small">
                                {formatPrice(item.price)}
                              </td>
                              <td className="text-end fw-semibold">
                                {formatPrice(item.price * item.quantity)}
                              </td>
                              <td className="text-center small">
                                {valItem ? (
                                  valItem.has_sufficient_stock ? (
                                    <span className="badge bg-success">
                                      <i className="bi bi-check-circle me-1"></i>In Stock
                                    </span>
                                  ) : (
                                    <span className="badge bg-danger">
                                      <i className="bi bi-x-circle me-1"></i>
                                      {valItem.available_stock <= 0
                                        ? "Out of Stock"
                                        : `Only ${valItem.available_stock} Left`}
                                    </span>
                                  )
                                ) : (
                                  <span className="badge bg-secondary">Unchecked</span>
                                )}
                              </td>
                              <td className="text-center">
                                {hasStockIssue && valItem.available_stock > 0 && (
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline-primary py-0 px-2 me-1"
                                    title="Adjust to maximum available stock"
                                    onClick={() => updateQuantity(item.id, valItem.available_stock)}
                                  >
                                    Set to {valItem.available_stock}
                                  </button>
                                )}
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline-danger py-0 px-1"
                                  title="Remove item"
                                  onClick={() => removeFromCart(item.id)}
                                >
                                  <i className="bi bi-trash"></i>
                                </button>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Customer Information Preview */}
                  <h6 className="fw-bold mb-3 border-top pt-3">
                    <i className="bi bi-truck me-2 text-primary"></i>Shipping Destination
                  </h6>
                  <div className="row g-2 mb-4 small">
                    <div className="col-md-6">
                      <label htmlFor={nameId} className="form-label text-muted mb-1">Full Name</label>
                      <input
                        id={nameId}
                        type="text"
                        className="form-control form-control-sm"
                        value={customer.name}
                        onChange={e => setCustomer({ ...customer, name: e.target.value })}
                      />
                    </div>
                    <div className="col-md-6">
                      <label htmlFor={emailId} className="form-label text-muted mb-1">Email</label>
                      <input
                        id={emailId}
                        type="email"
                        className="form-control form-control-sm"
                        value={customer.email}
                        onChange={e => setCustomer({ ...customer, email: e.target.value })}
                      />
                    </div>
                    <div className="col-12">
                      <label htmlFor={addressId} className="form-label text-muted mb-1">Street Address</label>
                      <input
                        id={addressId}
                        type="text"
                        className="form-control form-control-sm"
                        value={customer.address}
                        onChange={e => setCustomer({ ...customer, address: e.target.value })}
                      />
                    </div>
                    <div className="col-md-8">
                      <label htmlFor={cityId} className="form-label text-muted mb-1">City</label>
                      <input
                        id={cityId}
                        type="text"
                        className="form-control form-control-sm"
                        value={customer.city}
                        onChange={e => setCustomer({ ...customer, city: e.target.value })}
                      />
                    </div>
                    <div className="col-md-4">
                      <label htmlFor={zipId} className="form-label text-muted mb-1">Postal Code</label>
                      <input
                        id={zipId}
                        type="text"
                        className="form-control form-control-sm"
                        value={customer.zip}
                        onChange={e => setCustomer({ ...customer, zip: e.target.value })}
                      />
                    </div>
                  </div>

                  {/* Proceed to Payment Action */}
                  <button
                    type="button"
                    className="btn btn-primary w-100 py-2 fw-semibold d-flex align-items-center justify-content-center gap-2"
                    onClick={handleProceedToPayment}
                    disabled={validating}
                  >
                    {validating ? (
                      <>
                        <span className="spinner-border spinner-border-sm" role="status"></span>
                        Verifying Live Stock &amp; Catalog Prices...
                      </>
                    ) : (
                      <>
                        Proceed to Payment (Check Stock &amp; Price) <i className="bi bi-arrow-right"></i>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* PAGE 2: Payment Execution & Method Selection */}
              {currentStep === 2 && (
                <div className="card shadow-sm border-0 p-4 mb-4">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="fw-bold mb-0">
                      <i className="bi bi-credit-card-2-front me-2 text-primary"></i>Step 2: Payment &amp; Confirmation
                    </h5>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => setCurrentStep(1)}
                      disabled={submittingPayment}
                    >
                      <i className="bi bi-arrow-left me-1"></i> Back to Review
                    </button>
                  </div>

                  {/* Verified Notice */}
                  <div className="alert alert-success d-flex align-items-center gap-2 py-2 mb-4" role="alert">
                    <i className="bi bi-check-circle-fill text-success fs-5"></i>
                    <div className="small">
                      <strong>Inventory &amp; Pricing Verified:</strong> All items are confirmed in stock with locked catalog prices.
                    </div>
                  </div>

                  {paymentError && (
                    <div className="alert alert-danger" role="alert">
                      <strong>Payment Error:</strong> {paymentError}
                    </div>
                  )}

                  {/* Payment Method Selector */}
                  <h6 className="fw-bold mb-2">Select Payment Method</h6>
                  <div className="row g-2 mb-4">
                    <div className="col-4">
                      <div
                        className={`card p-3 text-center cursor-pointer border ${
                          paymentMethod === "card" ? "border-primary bg-light" : ""
                        }`}
                        style={{ cursor: "pointer" }}
                        onClick={() => setPaymentMethod("card")}
                      >
                        <i className="bi bi-credit-card fs-4 text-primary mb-1"></i>
                        <span className="small fw-semibold">Card</span>
                      </div>
                    </div>
                    <div className="col-4">
                      <div
                        className={`card p-3 text-center cursor-pointer border ${
                          paymentMethod === "upi" ? "border-primary bg-light" : ""
                        }`}
                        style={{ cursor: "pointer" }}
                        onClick={() => setPaymentMethod("upi")}
                      >
                        <i className="bi bi-qr-code-scan fs-4 text-success mb-1"></i>
                        <span className="small fw-semibold">UPI / QR</span>
                      </div>
                    </div>
                    <div className="col-4">
                      <div
                        className={`card p-3 text-center cursor-pointer border ${
                          paymentMethod === "cod" ? "border-primary bg-light" : ""
                        }`}
                        style={{ cursor: "pointer" }}
                        onClick={() => setPaymentMethod("cod")}
                      >
                        <i className="bi bi-cash-coin fs-4 text-dark mb-1"></i>
                        <span className="small fw-semibold">Cash on Delivery</span>
                      </div>
                    </div>
                  </div>

                  {/* Conditional Payment Method Inputs */}
                  {paymentMethod === "card" && (
                    <div className="bg-light p-3 rounded mb-4 border">
                      <h6 className="small fw-bold text-muted mb-2">Card Details</h6>
                      <div className="row g-2 small">
                        <div className="col-12">
                          <label htmlFor={cardNumId} className="form-label text-muted mb-1">Card Number</label>
                          <input
                            id={cardNumId}
                            type="text"
                            className="form-control form-control-sm"
                            value={cardDetails.number}
                            onChange={e => setCardDetails({ ...cardDetails, number: e.target.value })}
                          />
                        </div>
                        <div className="col-6">
                          <label htmlFor={cardExpId} className="form-label text-muted mb-1">Expiry Date</label>
                          <input
                            id={cardExpId}
                            type="text"
                            className="form-control form-control-sm"
                            value={cardDetails.expiry}
                            onChange={e => setCardDetails({ ...cardDetails, expiry: e.target.value })}
                          />
                        </div>
                        <div className="col-6">
                          <label htmlFor={cardCvvId} className="form-label text-muted mb-1">CVV</label>
                          <input
                            id={cardCvvId}
                            type="password"
                            className="form-control form-control-sm"
                            value={cardDetails.cvv}
                            onChange={e => setCardDetails({ ...cardDetails, cvv: e.target.value })}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {paymentMethod === "upi" && (
                    <div className="bg-light p-3 rounded mb-4 border">
                      <h6 className="small fw-bold text-muted mb-2">UPI Identification</h6>
                      <label htmlFor={upiId} className="form-label text-muted small mb-1">Virtual Payment Address (VPA)</label>
                      <input
                        id={upiId}
                        type="text"
                        className="form-control form-control-sm"
                        value={upiAddress}
                        onChange={e => setUpiAddress(e.target.value)}
                        placeholder="username@bank"
                      />
                    </div>
                  )}

                  {paymentMethod === "cod" && (
                    <div className="bg-light p-3 rounded mb-4 border text-muted small">
                      <i className="bi bi-info-circle me-1 text-primary"></i>
                      Pay in cash upon physical delivery. Exact change is appreciated.
                    </div>
                  )}

                  {/* Final Submit Payment Button */}
                  <button
                    type="button"
                    className="btn btn-success w-100 py-3 fw-bold fs-5 d-flex align-items-center justify-content-center gap-2"
                    onClick={handleFinalPayment}
                    disabled={submittingPayment}
                  >
                    {submittingPayment ? (
                      <>
                        <span className="spinner-border spinner-border-sm" role="status"></span>
                        Processing Payment &amp; Placing Order...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-lock-fill"></i> Pay &amp; Place Order ({formatPrice(grandTotal)})
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Right Column: Order Summary Card */}
            <div className="col-12 col-lg-4">
              <div className="card shadow-sm border-0 p-4 sticky-top" style={{ top: "80px" }}>
                <h5 className="fw-bold mb-3">
                  <i className="bi bi-receipt me-2 text-primary"></i>Order Summary
                </h5>

                <div className="d-flex justify-content-between small text-muted mb-2">
                  <span>Price (excl. 5% GST)</span>
                  <span>{formatPrice(subtotalWithoutGst)}</span>
                </div>

                <div className="d-flex justify-content-between small text-muted mb-2">
                  <span>Included 5% GST</span>
                  <span>{formatPrice(includedGst)}</span>
                </div>

                <div className="d-flex justify-content-between small fw-semibold text-dark mb-2 pt-2 border-top">
                  <span>Catalog Price (incl. GST)</span>
                  <span>{formatPrice(subtotal)}</span>
                </div>

                <div className="d-flex justify-content-between small text-muted mb-3">
                  <span>Platform Fee (1.5%)</span>
                  <span>{formatPrice(platformFee)}</span>
                </div>

                <div className="d-flex justify-content-between fw-bold fs-4 border-top pt-3 mb-3">
                  <span>Total Amount</span>
                  <span className="text-primary">{formatPrice(grandTotal)}</span>
                </div>

                <div className="bg-light p-3 rounded small text-muted border">
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <i className="bi bi-shield-lock-fill text-success"></i>
                    <strong className="text-dark">Zero-Overselling Guarantee</strong>
                  </div>
                  Stock is verified atomically in Redis via server-side Lua scripts upon completion.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Wrapper>
  )
}
