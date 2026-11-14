import { useEffect, useMemo, useState } from "react"
import { Wrapper } from "./wrapper"
import { inventoryApi } from "../api/client"
import { useCart } from "../context/CartContext"
import { formatDate, formatPrice, parseQuantity, calculatePriceWithoutGst, calculateGstAmount, calculatePlatformFee, calculateOrderTotal } from "../utils/formatters"

export const ProductsStore = () => {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState("")
  const [stockFilter, setStockFilter] = useState("all") // 'all' | 'in_stock' | 'out_of_stock'
  const [selectedCategory, setSelectedCategory] = useState("all") // 'all' | category name
  const [sortBy, setSortBy] = useState("name_asc") // 'name_asc' | 'price_asc' | 'price_desc' | 'stock_desc'

  // Per-product selected quantity for Add to Cart
  const [quantities, setQuantities] = useState({})

  // Product detail modal state
  const [selectedProduct, setSelectedProduct] = useState(null)

  // Toast feedback state
  const [toastMessage, setToastMessage] = useState(null)

  const { addToCart, setIsCartOpen } = useCart()

  const loadProducts = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await inventoryApi.getProducts()
      if (Array.isArray(data)) {
        setProducts(data)
      } else {
        setProducts([])
      }
    } catch (err) {
      console.error("Failed to load storefront products:", err)
      setError(err.message || "Failed to load products from Inventory service.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
  }, [])

  const handleQuantityChange = (productId, val, maxStock) => {
    const parsed = parseInt(val, 10)
    if (isNaN(parsed) || parsed < 1) {
      setQuantities(prev => ({ ...prev, [productId]: 1 }))
    } else {
      const clamped = Math.min(parsed, maxStock || 1)
      setQuantities(prev => ({ ...prev, [productId]: clamped }))
    }
  }

  const handleAddToCart = (product, openDrawer = false) => {
    const qty = quantities[product.id] || 1
    addToCart(product, qty)
    setToastMessage(`Added ${qty}x "${product.name}" to your cart!`)
    setTimeout(() => setToastMessage(null), 3000)

    if (openDrawer) {
      setIsCartOpen(true)
    }
  }

  // Distinct categories from products
  const categories = useMemo(() => {
    const set = new Set()
    products.forEach(p => {
      if (p.category && p.category.trim()) {
        set.add(p.category.trim())
      }
    })
    return ["all", ...Array.from(set)]
  }, [products])

  // Filtered and sorted products
  const filteredProducts = useMemo(() => {
    return products
      .filter(p => {
        const q = searchTerm.toLowerCase().trim()
        const matchesName = !q || p.name?.toLowerCase().includes(q) || p.category?.toLowerCase().includes(q)
        const itemCategory = (p.category && p.category.trim()) || "Uncategorized"
        const matchesCategory = selectedCategory === "all" || itemCategory.toLowerCase() === selectedCategory.toLowerCase()
        const qty = parseQuantity(p.quantity, 0)
        if (stockFilter === "in_stock") return matchesName && matchesCategory && qty > 0
        if (stockFilter === "out_of_stock") return matchesName && matchesCategory && qty <= 0
        return matchesName && matchesCategory
      })
      .sort((a, b) => {
        if (sortBy === "price_asc") return (parseFloat(a.price) || 0) - (parseFloat(b.price) || 0)
        if (sortBy === "price_desc") return (parseFloat(b.price) || 0) - (parseFloat(a.price) || 0)
        if (sortBy === "stock_desc") return parseQuantity(b.quantity, 0) - parseQuantity(a.quantity, 0)
        return (a.name || "").localeCompare(b.name || "")
      })
  }, [products, searchTerm, stockFilter, selectedCategory, sortBy])

  return (
    <Wrapper>
      {/* Toast alert */}
      {toastMessage && (
        <div
          className="position-fixed bottom-0 end-0 p-3"
          style={{ zIndex: 1060 }}
        >
          <div className="toast show align-items-center text-bg-success border-0 shadow" role="alert">
            <div className="d-flex">
              <div className="toast-body d-flex align-items-center gap-2">
                <i className="bi bi-cart-check-fill fs-5"></i>
                {toastMessage}
              </div>
              <button
                type="button"
                className="btn-close btn-close-white me-2 m-auto"
                onClick={() => setToastMessage(null)}
              ></button>
            </div>
          </div>
        </div>
      )}

      {/* Hero Banner */}
      <div className="p-4 p-md-5 mb-4 rounded-4 bg-dark text-white shadow-sm position-relative overflow-hidden">
        <div className="col-md-8 position-relative" style={{ zIndex: 1 }}>
          <span className="badge bg-primary text-uppercase px-2 py-1 mb-2 fw-semibold">
            Inventory Order System
          </span>
          <h1 className="display-5 fw-bold mb-3">Modern Storefront &amp; Flash Checkout</h1>
          <p className="lead mb-4 text-light">
            Real-time inventory backed by Redis OM, seamless order lifecycle on PostgreSQL,
            and automated async event streams.
          </p>
          <div className="d-flex flex-wrap gap-2">
            <a href="#catalog" className="btn btn-primary px-4 py-2 fw-semibold">
              <i className="bi bi-bag-check me-2"></i>Browse Products
            </a>
            <button
              type="button"
              className="btn btn-outline-light px-4 py-2"
              onClick={() => setIsCartOpen(true)}
            >
              <i className="bi bi-cart3 me-2"></i>Open Cart
            </button>
          </div>
        </div>
      </div>

      {/* Catalog Section */}
      <div id="catalog" className="mb-5">
        {/* Controls Bar: Search, Filters, Sort */}
        <div className="card shadow-sm border-0 mb-4 p-3 bg-white">
          <div className="row g-3 align-items-center">
            {/* Search */}
            <div className="col-12 col-md-5">
              <div className="input-group">
                <span className="input-group-text bg-light border-end-0">
                  <i className="bi bi-search text-muted"></i>
                </span>
                <input
                  type="text"
                  className="form-control border-start-0 ps-0 bg-light"
                  placeholder="Search products by name..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <button
                    className="btn btn-light border"
                    type="button"
                    onClick={() => setSearchTerm("")}
                  >
                    <i className="bi bi-x"></i>
                  </button>
                )}
              </div>
            </div>

            {/* Stock Filter Buttons */}
            <div className="col-12 col-md-4">
              <div className="btn-group w-100" role="group">
                <button
                  type="button"
                  className={`btn btn-sm ${stockFilter === "all" ? "btn-primary" : "btn-outline-secondary"}`}
                  onClick={() => setStockFilter("all")}
                >
                  All ({products.length})
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${stockFilter === "in_stock" ? "btn-primary" : "btn-outline-secondary"}`}
                  onClick={() => setStockFilter("in_stock")}
                >
                  In Stock ({products.filter(p => parseQuantity(p.quantity, 0) > 0).length})
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${stockFilter === "out_of_stock" ? "btn-primary" : "btn-outline-secondary"}`}
                  onClick={() => setStockFilter("out_of_stock")}
                >
                  Out of Stock ({products.filter(p => parseQuantity(p.quantity, 0) <= 0).length})
                </button>
              </div>
            </div>

            {/* Sort Dropdown */}
            <div className="col-12 col-md-3">
              <select
                className="form-select form-select-sm"
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
              >
                <option value="name_asc">Sort: Name (A &rarr; Z)</option>
                <option value="price_asc">Sort: Price (Low &rarr; High)</option>
                <option value="price_desc">Sort: Price (High &rarr; Low)</option>
                <option value="stock_desc">Sort: Stock (Highest First)</option>
              </select>
            </div>
          </div>

          {/* Category Filter Pills */}
          {categories.length > 1 && (
            <div className="d-flex flex-wrap align-items-center gap-2 mt-3 pt-2 border-top">
              <span className="small text-muted fw-semibold me-1">
                <i className="bi bi-tag me-1"></i>Categories:
              </span>
              {categories.map(cat => (
                <button
                  key={cat}
                  type="button"
                  className={`btn btn-sm ${
                    selectedCategory.toLowerCase() === cat.toLowerCase()
                      ? "btn-dark"
                      : "btn-outline-secondary"
                  } rounded-pill px-3 py-1`}
                  onClick={() => setSelectedCategory(cat)}
                >
                  {cat === "all" ? "All Categories" : cat}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div className="alert alert-danger d-flex justify-content-between align-items-center mb-4" role="alert">
            <div>
              <i className="bi bi-exclamation-triangle-fill me-2"></i>
              <strong>Connection Error:</strong> {error}
            </div>
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              onClick={loadProducts}
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading Spinner */}
        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status" style={{ width: "3rem", height: "3rem" }}>
              <span className="visually-hidden">Loading products...</span>
            </div>
            <p className="mt-3 text-muted">Connecting to Inventory Service (Port 8000)...</p>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="text-center py-5 bg-white rounded-3 shadow-sm p-4">
            <i className="bi bi-inbox display-4 text-muted mb-3 d-block"></i>
            <h5>No Products Found</h5>
            <p className="text-muted">
              {searchTerm || stockFilter !== "all"
                ? "No products match your current search and filter criteria."
                : "No products exist in the catalog yet."}
            </p>
            {(searchTerm || stockFilter !== "all") && (
              <button
                type="button"
                className="btn btn-sm btn-outline-primary mt-2"
                onClick={() => {
                  setSearchTerm("")
                  setStockFilter("all")
                }}
              >
                Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-3 row-cols-xl-4 g-4">
            {filteredProducts.map(product => {
              const qty = parseQuantity(product.quantity, 0)
              const inStock = qty > 0
              const selectedQty = quantities[product.id] || 1

              return (
                <div key={product.id} className="col">
                  <div className="card h-100 shadow-sm product-card border-0">
                    {/* Placeholder image representation */}
                    <div className="card-img-placeholder position-relative">
                      <i className="bi bi-box-seam"></i>
                      <span
                        className={`position-absolute top-0 end-0 m-2 badge stock-pill ${
                          inStock ? "bg-success" : "bg-danger"
                        }`}
                      >
                        {inStock ? `In Stock (${qty})` : "Out of Stock"}
                      </span>
                    </div>

                    <div className="card-body d-flex flex-column p-3">
                      <h5 className="card-title text-truncate fw-bold mb-1" title={product.name}>
                        {product.name}
                      </h5>
                      <div className="d-flex align-items-center justify-content-between mb-2">
                        <span className="badge bg-light text-secondary border small">
                          <i className="bi bi-tag me-1"></i>{product.category || "Uncategorized"}
                        </span>
                        <span className="text-muted font-monospace small">{product.id.slice(0, 8)}...</span>
                      </div>

                      <div className="mt-auto pt-2">
                        <div className="d-flex align-items-baseline justify-content-between mb-1">
                          <span className="fs-4 fw-bold text-primary">
                            {formatPrice(product.price)}
                          </span>
                          <span className="text-secondary small">
                            (incl. 5% GST)
                          </span>
                        </div>
                        <div className="d-flex justify-content-between small text-muted mb-3">
                          <span>Excl. GST: {formatPrice(calculatePriceWithoutGst(product.price))}</span>
                          <span>+1.5% platform fee</span>
                        </div>

                        {/* Quantity picker & Actions */}
                        {inStock ? (
                          <div className="d-flex flex-column gap-2">
                            <div className="input-group input-group-sm">
                              <span className="input-group-text bg-light">Qty</span>
                              <input
                                type="number"
                                className="form-control text-center"
                                min="1"
                                max={qty}
                                value={selectedQty}
                                onChange={e => handleQuantityChange(product.id, e.target.value, qty)}
                              />
                              <button
                                type="button"
                                className="btn btn-outline-primary"
                                onClick={() => handleAddToCart(product, false)}
                                title="Add to cart"
                              >
                                <i className="bi bi-cart-plus me-1"></i> Add
                              </button>
                            </div>
                            <button
                              type="button"
                              className="btn btn-sm btn-primary w-100"
                              onClick={() => handleAddToCart(product, true)}
                            >
                              <i className="bi bi-lightning-fill me-1"></i> Buy Now
                            </button>
                          </div>
                        ) : (
                          <button type="button" className="btn btn-sm btn-secondary w-100" disabled>
                            Currently Unavailable
                          </button>
                        )}

                        <button
                          type="button"
                          className="btn btn-link btn-sm text-decoration-none w-100 mt-2 p-0 text-muted"
                          onClick={() => setSelectedProduct(product)}
                        >
                          <i className="bi bi-info-circle me-1"></i> View Specifications
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Product Details Modal */}
      {selectedProduct && (
        <>
          <div
            className="modal-backdrop fade show"
            style={{ zIndex: 1050 }}
            onClick={() => setSelectedProduct(null)}
          ></div>
          <div
            className="modal fade show d-block"
            tabIndex="-1"
            style={{ zIndex: 1055 }}
          >
            <div className="modal-dialog modal-dialog-centered">
              <div className="modal-content shadow-lg border-0">
                <div className="modal-header">
                  <h5 className="modal-title fw-bold">
                    <i className="bi bi-box-seam me-2 text-primary"></i>
                    {selectedProduct.name}
                  </h5>
                  <button
                    type="button"
                    className="btn-close"
                    aria-label="Close"
                    onClick={() => setSelectedProduct(null)}
                  ></button>
                </div>
                <div className="modal-body">
                  <div className="mb-3">
                    <span
                      className={`badge ${
                        parseQuantity(selectedProduct.quantity, 0) > 0 ? "bg-success" : "bg-danger"
                      }`}
                    >
                      {parseQuantity(selectedProduct.quantity, 0) > 0
                        ? `In Stock: ${selectedProduct.quantity} units`
                        : "Out of Stock"}
                    </span>
                  </div>
                  <dl className="row small">
                    <dt className="col-sm-4 text-muted">Category:</dt>
                    <dd className="col-sm-8 fw-semibold">{selectedProduct.category || "Uncategorized"}</dd>

                    <dt className="col-sm-4 text-muted">Primary Key (PK):</dt>
                    <dd className="col-sm-8 font-monospace">{selectedProduct.id}</dd>

                    <dt className="col-sm-4 text-muted">Price (excl. GST):</dt>
                    <dd className="col-sm-8">{formatPrice(calculatePriceWithoutGst(selectedProduct.price))}</dd>

                    <dt className="col-sm-4 text-muted">Included 5% GST:</dt>
                    <dd className="col-sm-8 text-secondary">{formatPrice(calculateGstAmount(selectedProduct.price))}</dd>

                    <dt className="col-sm-4 text-muted">Main Price (incl. GST):</dt>
                    <dd className="col-sm-8 fw-bold text-primary fs-6">
                      {formatPrice(selectedProduct.price)}
                    </dd>

                    <dt className="col-sm-4 text-muted">Platform Fee (1.5%):</dt>
                    <dd className="col-sm-8 text-secondary">
                      {formatPrice(calculatePlatformFee(selectedProduct.price))}
                    </dd>

                    <dt className="col-sm-4 text-muted">Total Per Unit:</dt>
                    <dd className="col-sm-8 fw-semibold text-primary">
                      {formatPrice(calculateOrderTotal(selectedProduct.price, 1))}
                    </dd>

                    <dt className="col-sm-4 text-muted">Registered On:</dt>
                    <dd className="col-sm-8">{formatDate(selectedProduct.creation_time)}</dd>
                  </dl>
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-outline-secondary"
                    onClick={() => setSelectedProduct(null)}
                  >
                    Close
                  </button>
                  {parseQuantity(selectedProduct.quantity, 0) > 0 && (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => {
                        handleAddToCart(selectedProduct, true)
                        setSelectedProduct(null)
                      }}
                    >
                      <i className="bi bi-cart-plus me-1"></i> Add to Cart &amp; Checkout
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </Wrapper>
  )
}
