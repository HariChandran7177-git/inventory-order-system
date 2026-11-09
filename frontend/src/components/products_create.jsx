import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { Wrapper } from "./wrapper"
import { inventoryApi } from "../api/client"

export const ProductsCreate = () => {
  const [name, setName] = useState("")
  const [price, setPrice] = useState("")
  const [quantity, setQuantity] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)
  const navigate = useNavigate()

  const submit = async e => {
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
      await inventoryApi.createProduct({
        name: name.trim(),
        price: parsedPrice,
        quantity: parsedQuantity,
      })

      // Navigate safely to admin inventory list
      navigate("/admin")
    } catch (err) {
      console.error("Failed to add product:", err)
      setErrorMessage(err.message || "Failed to create product in Inventory service.")
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
                Add Product
              </li>
            </ol>
          </nav>

          <div className="card shadow-sm border-0">
            <div className="card-header bg-white py-3 border-bottom">
              <h4 className="card-title fw-bold mb-0">
                <i className="bi bi-plus-circle me-2 text-success"></i>
                Add New Product
              </h4>
              <small className="text-muted">Register a new catalog item in Redis OM</small>
            </div>

            <div className="card-body p-4">
              {errorMessage && (
                <div className="alert alert-danger" role="alert">
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  {errorMessage}
                </div>
              )}

              <form onSubmit={submit}>
                <div className="form-floating mb-3">
                  <input
                    id="new-prod-name"
                    className="form-control"
                    placeholder="Product Name"
                    value={name}
                    required
                    onChange={e => setName(e.target.value)}
                  />
                  <label htmlFor="new-prod-name">Product Name</label>
                </div>

                <div className="form-floating mb-3">
                  <input
                    id="new-prod-price"
                    type="number"
                    step="0.01"
                    min="0"
                    className="form-control"
                    placeholder="Price"
                    value={price}
                    required
                    onChange={e => setPrice(e.target.value)}
                  />
                  <label htmlFor="new-prod-price">Unit Price ($)</label>
                </div>

                <div className="form-floating mb-4">
                  <input
                    id="new-prod-quantity"
                    type="number"
                    min="0"
                    className="form-control"
                    placeholder="Quantity"
                    value={quantity}
                    required
                    onChange={e => setQuantity(e.target.value)}
                  />
                  <label htmlFor="new-prod-quantity">Initial Stock Quantity</label>
                </div>

                {/* Fixed Flexbox Button Layout */}
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-success flex-grow-1 py-2 fw-semibold"
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                        Saving to Inventory...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-check-lg me-1"></i> Create Product
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
            </div>
          </div>
        </div>
      </div>
    </Wrapper>
  )
}
