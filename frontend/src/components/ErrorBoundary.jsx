import React from "react"

/**
 * Robust React Error Boundary
 * Catches JavaScript errors anywhere in the child component tree,
 * logs the errors, and displays a user-friendly fallback UI.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    window.location.href = "/"
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container py-5">
          <div className="row justify-content-center">
            <div className="col-12 col-md-8 col-lg-6">
              <div className="card shadow-sm border-danger">
                <div className="card-header bg-danger text-white d-flex align-items-center gap-2">
                  <i className="bi bi-exclamation-triangle-fill fs-5"></i>
                  <h5 className="mb-0">Something went wrong</h5>
                </div>
                <div className="card-body p-4">
                  <p className="card-text text-muted">
                    An unexpected error occurred while rendering the application. You can return
                    to the storefront or reload the page.
                  </p>
                  {this.state.error && (
                    <div className="alert alert-secondary text-monospace small mb-3">
                      <strong>Error:</strong> {this.state.error.toString()}
                    </div>
                  )}
                  {this.state.errorInfo && (
                    <details className="small text-muted mb-3">
                      <summary className="cursor-pointer">Component Stack Details</summary>
                      <pre className="mt-2 p-2 bg-light rounded" style={{ maxHeight: "200px", overflow: "auto" }}>
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </details>
                  )}
                  <div className="d-flex gap-2">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={this.handleReset}
                    >
                      <i className="bi bi-house-door me-1"></i> Return to Storefront
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary"
                      onClick={() => window.location.reload()}
                    >
                      <i className="bi bi-arrow-clockwise me-1"></i> Reload Page
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
