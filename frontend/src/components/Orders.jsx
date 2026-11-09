import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Wrapper } from "./wrapper"
import { paymentApi } from "../api/client"
import { formatDate, formatPrice } from "../utils/formatters"

export const Orders = () => {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [deletingId, setDeletingId] = useState(null)

  const fetchOrders = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true)
    else setLoading(true)
    setError(null)

    try {
      const data = await paymentApi.getOrders()
      if (Array.isArray(data)) {
        setOrders(data)
      } else {
        setOrders([])
      }
    } catch (err) {
      console.error("Failed to fetch orders:", err)
      setError(err.message || "Unable to connect to Payment Service.")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const handleDelete = async orderId => {
    if (!window.confirm(`Are you sure you want to delete Order #${orderId}?`)) return
    setDeletingId(orderId)
    try {
      await paymentApi.deleteOrder(orderId)
      // Functional updater to avoid stale closure
      setOrders(prev => prev.filter(o => o.order_id !== orderId))
    } catch (err) {
      alert(`Failed to delete order #${orderId}: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  const filteredOrders = useMemo(() => {
    return orders.filter(order => {
      const matchesStatus =
        statusFilter === "all" ||
        order.status?.toLowerCase() === statusFilter.toLowerCase()
      const matchesSearch =
        searchQuery === "" ||
        String(order.order_id).includes(searchQuery) ||
        order.product_id?.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesStatus && matchesSearch
    })
  }, [orders, statusFilter, searchQuery])

  // Aggregate stats
  const totalCompleted = orders.filter(o => o.status === "completed").length
  const totalPending = orders.filter(o => o.status === "pending").length
  const totalRefunded = orders.filter(o => o.status === "refunded").length

  return (
    <Wrapper>
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-4">
        <div>
          <h2 className="fw-bold mb-1">
            <i className="bi bi-receipt me-2 text-primary"></i> Order Tracking &amp; History
          </h2>
          <p className="text-muted mb-0">
            Real-time status updates from the PostgreSQL persistence layer and Redis Stream workers.
          </p>
        </div>
        <div className="d-flex gap-2 mt-3 mt-md-0">
          <button
            type="button"
            className="btn btn-outline-primary d-flex align-items-center gap-2"
            onClick={() => fetchOrders(true)}
            disabled={loading || refreshing}
          >
            <i className={`bi bi-arrow-clockwise ${refreshing ? "spin" : ""}`}></i>
            {refreshing ? "Refreshing..." : "Refresh Status"}
          </button>
          <Link to="/" className="btn btn-primary d-flex align-items-center gap-1">
            <i className="bi bi-shop"></i> Storefront
          </Link>
        </div>
      </div>

      {/* Aggregate Statistics Cards */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 border-start border-primary border-4 p-3 bg-white">
            <div className="text-muted small text-uppercase fw-semibold">Total Orders</div>
            <div className="fs-3 fw-bold text-dark">{orders.length}</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 border-start border-warning border-4 p-3 bg-white">
            <div className="text-muted small text-uppercase fw-semibold">Pending Saga</div>
            <div className="fs-3 fw-bold text-warning">{totalPending}</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 border-start border-success border-4 p-3 bg-white">
            <div className="text-muted small text-uppercase fw-semibold">Completed</div>
            <div className="fs-3 fw-bold text-success">{totalCompleted}</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 border-start border-danger border-4 p-3 bg-white">
            <div className="text-muted small text-uppercase fw-semibold">Refunded / Failed</div>
            <div className="fs-3 fw-bold text-danger">{totalRefunded}</div>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="alert alert-danger d-flex justify-content-between align-items-center mb-4" role="alert">
          <div>
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            <strong>Payment Service Error:</strong> {error}
          </div>
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            onClick={() => fetchOrders()}
          >
            Retry
          </button>
        </div>
      )}

      {/* Search and Filters */}
      <div className="card shadow-sm border-0 mb-4 p-3 bg-white">
        <div className="row g-3 align-items-center">
          <div className="col-12 col-md-6">
            <div className="input-group input-group-sm">
              <span className="input-group-text bg-light">
                <i className="bi bi-search"></i>
              </span>
              <input
                type="text"
                className="form-control"
                placeholder="Search by Order ID or Product ID..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="col-12 col-md-6">
            <div className="btn-group btn-group-sm w-100" role="group">
              <button
                type="button"
                className={`btn ${statusFilter === "all" ? "btn-primary" : "btn-outline-secondary"}`}
                onClick={() => setStatusFilter("all")}
              >
                All
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === "completed" ? "btn-success" : "btn-outline-secondary"}`}
                onClick={() => setStatusFilter("completed")}
              >
                Completed
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === "pending" ? "btn-warning" : "btn-outline-secondary"}`}
                onClick={() => setStatusFilter("pending")}
              >
                Pending
              </button>
              <button
                type="button"
                className={`btn ${statusFilter === "refunded" ? "btn-danger" : "btn-outline-secondary"}`}
                onClick={() => setStatusFilter("refunded")}
              >
                Refunded
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Orders Table */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading orders...</span>
          </div>
          <p className="mt-2 text-muted">Retrieving transactions from Payment Service (Port 8001)...</p>
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="text-center py-5 bg-white rounded-3 shadow-sm p-4">
          <i className="bi bi-receipt-cutoff display-4 text-muted mb-3 d-block"></i>
          <h5>No Orders Found</h5>
          <p className="text-muted">
            {orders.length === 0
              ? "You haven't placed any orders yet. Visit our storefront to add items and checkout!"
              : "No orders match your filter criteria."}
          </p>
          <Link to="/" className="btn btn-primary mt-2">
            <i className="bi bi-cart3 me-1"></i> Start Shopping
          </Link>
        </div>
      ) : (
        <div className="card shadow-sm border-0 overflow-hidden">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th scope="col" className="ps-3">Order #</th>
                  <th scope="col">Product ID</th>
                  <th scope="col" className="text-center">Quantity</th>
                  <th scope="col" className="text-end">Unit Price</th>
                  <th scope="col" className="text-end">Fee/Unit (20%)</th>
                  <th scope="col" className="text-end">Total Amount</th>
                  <th scope="col" className="text-center">Status</th>
                  <th scope="col">Placed At</th>
                  <th scope="col" className="text-center pe-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map(order => {
                  let statusBadgeClass = "bg-secondary"
                  let statusIcon = "bi-question-circle"
                  const st = order.status?.toLowerCase()

                  if (st === "completed") {
                    statusBadgeClass = "bg-success"
                    statusIcon = "bi-check-circle"
                  } else if (st === "pending") {
                    statusBadgeClass = "bg-warning text-dark"
                    statusIcon = "bi-hourglass-split"
                  } else if (st === "refunded") {
                    statusBadgeClass = "bg-danger"
                    statusIcon = "bi-arrow-counterclockwise"
                  }

                  return (
                    <tr key={order.order_id}>
                      <td className="ps-3 fw-bold text-dark">
                        #{order.order_id}
                      </td>
                      <td className="font-monospace small text-muted">
                        {order.product_id}
                      </td>
                      <td className="text-center fw-semibold">
                        {order.order_quantity}
                      </td>
                      <td className="text-end text-muted">
                        {formatPrice(order.price)}
                      </td>
                      <td className="text-end text-secondary small">
                        {formatPrice(order.fee_per_unit)}
                      </td>
                      <td className="text-end fw-bold text-primary">
                        {formatPrice(order.total)}
                      </td>
                      <td className="text-center">
                        <span className={`badge ${statusBadgeClass} d-inline-flex align-items-center gap-1 px-2 py-1`}>
                          <i className={`bi ${statusIcon}`}></i>
                          {order.status}
                        </span>
                      </td>
                      <td className="small text-muted">
                        {formatDate(order.created_at)}
                      </td>
                      <td className="text-center pe-3">
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          title="Delete Order"
                          disabled={deletingId === order.order_id}
                          onClick={() => handleDelete(order.order_id)}
                        >
                          {deletingId === order.order_id ? (
                            <span className="spinner-border spinner-border-sm"></span>
                          ) : (
                            <i className="bi bi-trash"></i>
                          )}
                        </button>
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
