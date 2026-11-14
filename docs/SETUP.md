# Local Setup

## Requirements

- Python 3.10+ (existing local `.venv` uses Python 3.11).
- Node.js 20+ and npm.
- Redis server running on `localhost:6379`.
- PostgreSQL 16 server running on `localhost:5432`.

## Environment Setup

From the repository root:

```powershell
Copy-Item .env.example .env
npm install
```

## Running the Services

Launch each service in a separate terminal:

### 1. Inventory API (Port 8000)
```powershell
npm run dev:inventory
```
Or directly: `.\.venv\Scripts\uvicorn.exe inventory.app.main:app --port 8000 --reload`

### 2. Payment API (Port 8001)
```powershell
npm run dev:payment
```
Or directly: `.\.venv\Scripts\uvicorn.exe payment.app.main:app --port 8001 --reload`

### 3. Frontend Storefront (Port 3000)
```powershell
npm run dev:frontend
```

Open the storefront at `http://localhost:3000`, inventory docs at `http://localhost:8000/docs`, and payment docs at `http://localhost:8001/docs`. The admin inventory route is `http://localhost:3000/admin`.

### 4. Background Stream Workers (Optional)
To run asynchronous event processing for Redis Streams:

```powershell
# Inventory consumer (stock decrement)
npm run dev:inventory-worker

# Payment consumer (refunds)
npm run dev:payment-worker
```

## Environment and Credentials

`.env.example` provides local defaults. Copy it to `.env`, which is ignored by Git. The example PostgreSQL password is a development placeholder. There is no authentication configured for the APIs.

## Connectivity and Offline Behavior

Bootstrap CSS/JavaScript and Bootstrap Icons are installed as npm dependencies and bundled by Vite; the app does not fetch UI assets from a CDN. All application services run natively on local ports without internet once dependencies are installed.
