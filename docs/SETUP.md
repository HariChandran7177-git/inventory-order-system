# Local Setup

## Requirements

- Python 3.10+ (the checked-in service images use Python 3.10; the existing local `.venv` is Python 3.11).
- Node.js 20+ and npm.
- Docker Desktop with its Linux engine running for the complete stack.

## Start the complete local stack

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open the storefront at `http://localhost:3000`, inventory at `http://localhost:8000/docs`, and orders at `http://localhost:8001/docs`. The correct inventory administration route is `http://localhost:3000/admin`.

Stop while retaining database volumes with `Ctrl+C` then `docker compose down`. To remove persisted local database data too, use `docker compose down -v` (destructive to local Redis/PostgreSQL data).

## Run frontend separately

```powershell
npm ci
npm run dev:frontend
```

The frontend expects reachable APIs at `VITE_API_URL` (default `http://localhost:8000`) and `VITE_PAYMENT_API_URL` (default `http://localhost:8001`). Set those in `.env` before starting Vite; Vite variables are bundled into the browser and must not contain secrets.

## Run API services as native processes

Start Redis and PostgreSQL first (Compose is the supported local path):

```powershell
docker compose up -d redis postgres
```

In separate PowerShell windows, with the root `.venv` activated:

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn inventory.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn payment.app.main:app --host 127.0.0.1 --port 8001
```

For the complete order lifecycle, also run workers in separate windows:

```powershell
$env:PYTHONPATH = "backend"
python -m inventory.app.workers.consumer
```

```powershell
$env:PYTHONPATH = "backend"
python -m payment.app.workers.consumer
```

Install Python requirements with `python -m pip install -r requirements.txt -r requirements-testing.txt` when creating a fresh development environment. Compose is the recommended way to ensure Redis/PostgreSQL hostnames, ports, and service ordering are consistent.

## Environment and local-only credentials

`.env.example` provides local defaults. Copy it to `.env`, which is ignored by Git. The example PostgreSQL password is intentionally a development placeholder and must be replaced for any shared environment. There is no authentication configured for the APIs. See [Deployment](DEPLOYMENT.md) for production blockers.

## Connectivity and offline behavior

Bootstrap CSS/JavaScript and Bootstrap Icons are installed as npm dependencies and bundled by Vite; the app no longer fetches UI assets from a CDN. After dependencies and container images are installed, all application services can run locally without internet, provided the Docker engine is available. Product/order functions require the local Redis and PostgreSQL services. Browser API calls use configured local service URLs; there is no bundled API mock or fake data fallback. Dependency installation and fetching Docker images require internet (or a pre-populated local cache).
