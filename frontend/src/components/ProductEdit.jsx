import { useEffect, useState } from "react"
import { useNavigate, useParams, Link } from "react-router-dom"
import { Wrapper } from "./wrapper"
import { inventoryApi } from "../api/client"

export const ProductEdit = () => {
  const { id } = useParams()
  const navigate = useNavigate()

  const [name, setName] = useState("")
  const [price, setPrice] = useState("")
  const [quantity, setQuantity] = useState("")
  const [category, setCategory] = useState("")
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)

  useEffect(() => {
    let isMounted = true
    const fetchProduct = async () => {
      try {
        const product = await inventoryApi.getProduct(id)
        if (isMounted && product) {
          setName(product.name || "")
          setPrice(product.price !== undefined ? String(product.price) : "")
          setQuantity(product.quantity !== undefined ? String(product.quantity) : "")
          setCategory(product.category || "")
        }
      } catch (err) {
        if (isMounted) {
          setErrorMessage(err.message || "Failed to load product details.")
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    fetchProduct()
    return () => {
      isMounted = false
    }
  }, [id])

  const handleSubmit = async e => {
    e.preventDefault()
    setErrorMessage(null)

    const parsedPrice = parseFloat(price)
    const parsedQuantity = parseInt(quantity, 10)

    if (!name.trim()) {
      setErrorMessage("Product name is required.")
      return
    }
    if (isNaN(parsedPrice) || parsedPrice < 0) {
      setErrorMessage("Please enter a valid price (greater than or equal to 0).")
      return
    }
    if (isNaN(parsedQuantity) || parsedQuantity < 0) {
      setErrorMessage("Please enter a valid quantity (greater than or equal to 0).")
      return
    }

    setSubmitting(true)

    try {
      await inventoryApi.updateProduct(id, {
        name: name.trim(),
        price: parsedPrice,
        quantity: parsedQuantity,
        category: category.trim() || "Uncategorized",
      })
      navigate("/admin")
    } catch (err) {
      console.error("Failed to update product:", err)
      setErrorMessage(err.message || "Failed to update product.")
      setSubmitting(false)
    }
  }

  return (
    <Wrapper>
      <div className="row justify-content-center">
        <div className="col-12 col-md-8 col-lg-6">
          <nav aria-label="breadcrumb" className="mb-3">
            <ol className="breadcrumb">
              <li className="breadcrumb-item">
                <Link to="/admin">Inventory</Link>
              </li>
              <li className="breadcrumb-item active" aria-current="page">
                Edit Product
              </li>
            </ol>
          </nav>

          <div className="card shadow-sm border-0">
            <div className="card-header bg-white py-3 border-bottom">
              <h4 className="card-title fw-bold mb-0">
                <i className="bi bi-pencil-square me-2 text-primary"></i>
                Edit Product
              </h4>
              <small className="text-muted font-monospace">PK: {id}</small>
            </div>

            <div className="card-body p-4">
              {errorMessage && (
                <div className="alert alert-danger" role="alert">
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  {errorMessage}
                </div>
              )}

              {loading ? (
                <div className="text-center py-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Loading product...</span>
                  </div>
                  <p className="mt-2 text-muted">Retrieving product from Redis OM...</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit}>
                  <div className="form-floating mb-3">
                    <input
                      id="edit-prod-name"
                      className="form-control"
                      placeholder="Product Name"
                      value={name}
                      required
                      onChange={e => setName(e.target.value)}
                    />
                    <label htmlFor="edit-prod-name">Product Name</label>
                  </div>

                  <div className="form-floating mb-3">
                    <input
                      id="edit-prod-category"
                      className="form-control"
                      placeholder="Category"
                      value={category}
                      onChange={e => setCategory(e.target.value)}
                    />
                    <label htmlFor="edit-prod-category">Category (e.g. Electronics, Clothing)</label>
                  </div>

                  <div className="form-floating mb-3">
                    <input
                      id="edit-prod-price"
                      type="number"
                      step="0.01"
                      min="0"
                      className="form-control"
                      placeholder="Price"
                      value={price}
                      required
                      onChange={e => setPrice(e.target.value)}
                    />
                    <label htmlFor="edit-prod-price">Unit Price ($)</label>
                  </div>

                  <div className="form-floating mb-4">
                    <input
                      id="edit-prod-quantity"
                      type="number"
                      min="0"
                      className="form-control"
                      placeholder="Stock Quantity"
                      value={quantity}
                      required
                      onChange={e => setQuantity(e.target.value)}
                    />
                    <label htmlFor="edit-prod-quantity">Stock Quantity</label>
                  </div>

                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-primary flex-grow-1 py-2 fw-semibold"
                      type="submit"
                      disabled={submitting}
                    >
                      {submitting ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2"></span>
                          Saving Changes...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-check-lg me-1"></i> Save Changes
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary px-4 py-2"
                      onClick={() => navigate("/admin")}
                      disabled={submitting}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </Wrapper>
  )
}
