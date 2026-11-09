import { Link } from "react-router-dom"
import { Wrapper } from "./wrapper"

export const NotFound = () => {
  return (
    <Wrapper>
      <div className="container py-5 text-center">
        <div className="row justify-content-center">
          <div className="col-12 col-md-8 col-lg-6">
            <div className="mb-4 text-primary">
              <i className="bi bi-compass display-1"></i>
            </div>
            <h1 className="display-4 fw-bold mb-2">404</h1>
            <h3 className="fw-semibold mb-3">Page Not Found</h3>
            <p className="lead text-muted mb-4">
              Sorry, the page you are looking for doesn't exist, has been removed, or is
              temporarily unavailable.
            </p>
            <div className="d-flex justify-content-center gap-3">
              <Link to="/" className="btn btn-primary px-4 py-2">
                <i className="bi bi-house-door me-2"></i>Return to Storefront
              </Link>
              <Link to="/admin" className="btn btn-outline-secondary px-4 py-2">
                <i className="bi bi-boxes me-2"></i>Admin Inventory
              </Link>
            </div>
          </div>
        </div>
      </div>
    </Wrapper>
  )
}
