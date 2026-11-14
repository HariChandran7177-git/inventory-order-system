import { useEffect, useMemo, useState } from "react"
import { Wrapper } from "./wrapper"
import { Link } from "react-router-dom"
import { inventoryApi } from "../api/client"
import { formatDate, formatPrice } from "../utils/formatters"

export const Products = () => {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [searchQuery, setSearchQuery] = useState("")

  const loadProducts = async () => {
    setLoading(true)
    setError(null)
    try {
      const content = await inventoryApi.getProducts()
      if (Array.isArray(content)) {
        setProducts(content)
      } else {
        setProducts([])
      }
    } catch (err) {
      console.error("Failed to fetch products:", err)
      setError(err.message || "Failed to load products from Inventory Service.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
  }, [])

  const del = async id => {
    if (!window.confirm("Are you sure you want to delete this product?")) {
      return
    }

    setDeletingId(id)
    try {
      await inventoryApi.deleteProduct(id)
      // Functional updater to eliminate stale closure
      setProducts(prev => prev.filter(product => product.id !== id))
    } catch (err) {
      console.error("Error deleting product:", err)
      alert(`Failed to delete product: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  const filteredProducts = useMemo(() => {
    return products.filter(product => {
      if (!searchQuery) return true
      const q = searchQuery.toLowerCase()
      return (
        product.name?.toLowerCase().includes(q) ||
        product.id?.toLowerCase().includes(q) ||
        product.category?.toLowerCase().includes(q)
      )
    })
  }, [products, searchQuery])

  return (
    <Wrapper>
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">
            <i className="bi bi-boxes me-2 text-primary"></i> Inventory Management
          </h2>
          <p className="text-muted mb-0">
            Direct real-time catalog management backed by Redis OM (Port 8000).
          </p>
        </div>
        <div className="d-flex gap-2 mt-3 mt-md-0">
          <button
            type="button"
            className="btn btn-outline-secondary d-flex align-items-center gap-1"
            onClick={loadProducts}
            disabled={loading}
          >
            <i className="bi bi-arrow-clockwise"></i> Refresh
          </button>
          <Link to="/admin/create" className="btn btn-success d-flex align-items-center gap-1">
            <i className="bi bi-plus-circle me-1"></i> Add New Product
          </Link>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger d-flex justify-content-between align-items-center mb-4" role="alert">
          <div>
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            <strong>Inventory Service Error:</strong> {error}
          </div>
          <button type="button" className="btn btn-sm btn-outline-danger" onClick={loadProducts}>
            Retry
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="card shadow-sm border-0 mb-4 p-3 bg-white">
        <div className="row align-items-center">
          <div className="col-12 col-md-6">
            <div className="input-group input-group-sm">
              <span className="input-group-text bg-light">
                <i className="bi bi-search"></i>
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Search products by name or PK..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="btn btn-light border"
                  onClick={() => setSearchQuery("")}
                >
                  <i className="bi bi-x"></i>
                </button>
              )}
            </div>
          </div>
          <div className="col-12 col-md-6 text-md-end text-muted small mt-2 mt-md-0">
            Total registered products: <strong>{products.length}</strong>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading products...</span>
          </div>
          <p className="mt-2 text-muted">Retrieving inventory from Redis OM...</p>
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="text-center py-5 bg-white rounded-3 shadow-sm p-4">
          <i className="bi bi-box-seam display-4 text-muted mb-3 d-block"></i>
          <h5>No Products Found</h5>
          <p className="text-muted">
            {searchQuery
              ? "No products match your search query."
              : "No inventory records exist. Add your first product using the button above."}
          </p>
          <Link to="/admin/create" className="btn btn-success mt-2">
            <i className="bi bi-plus-circle me-1"></i> Add Product Now
          </Link>
        </div>
      ) : (
        <div className="card shadow-sm border-0 overflow-hidden">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th scope="col" className="ps-3"># Primary Key</th>
                  <th scope="col">Product Name</th>
                  <th scope="col">Category</th>
                  <th scope="col" className="text-end">Unit Price</th>
                  <th scope="col" className="text-center">Stock Quantity</th>
                  <th scope="col">Registered Time</th>
                  <th scope="col" className="text-center pe-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map(product => {
                  const qty = parseInt(product.quantity, 10) || 0
                  return (
                    <tr key={product.id}>
                      <td className="ps-3 font-monospace small text-muted">
                        {product.id}
                      </td>
                      <td className="fw-semibold text-dark">
                        {product.name}
                      </td>
                      <td>
                        <span className="badge bg-light text-dark border">
                          {product.category || "Uncategorized"}
                        </span>
                      </td>
                      <td className="text-end fw-bold text-primary">
                        {formatPrice(product.price)}
                      </td>
                      <td className="text-center">
                        <span
                          className={`badge ${
                            qty > 10
                              ? "bg-success"
                              : qty > 0
                              ? "bg-warning text-dark"
                              : "bg-danger"
                          }`}
                        >
                          {qty > 0 ? `${qty} in stock` : "Out of stock"}
                        </span>
                      </td>
                      <td className="small text-muted">
                        {formatDate(product.creation_time)}
                      </td>
                      <td className="text-center pe-3">
                        <div className="btn-group btn-group-sm" role="group">
                          <Link
                            to={`/admin/edit/${product.id}`}
                            className="btn btn-outline-primary"
                            title="Edit product"
                          >
                            <i className="bi bi-pencil"></i> Edit
                          </Link>
                          <button
                            type="button"
                            className="btn btn-outline-danger"
                            title="Delete product"
                            disabled={deletingId === product.id}
                            onClick={() => del(product.id)}
                          >
                            {deletingId === product.id ? (
                              <span className="spinner-border spinner-border-sm"></span>
                            ) : (
                              <>
                                <i className="bi bi-trash"></i> Delete
                              </>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Wrapper>
  )
}
