# Deployment

## Current status

This repository is configured for local Docker Compose development. It is not production-ready for public deployment: no authentication/authorization, production database migrations, TLS/reverse proxy, secrets manager, production container build for the SPA, or production orchestration is configured. `/health` currently checks only that the API process responds.

There is no Netlify configuration in the repository and no connected Netlify tool/account in the current session. Netlify can serve the static frontend, but it cannot by itself provide the Redis instance, PostgreSQL database, two persistent FastAPI APIs, and two stream consumers required by the current application. Deploying only the static page would not make catalog/order functions work.

## Frontend hosting requirements

Build using `npm ci` then `npm run build:frontend`; Vite outputs `frontend/dist`. Configure `VITE_API_URL` and `VITE_PAYMENT_API_URL` at build time to HTTPS production API origins. These values are public. Configure SPA fallback/rewrite so unknown paths serve `/index.html` (the app uses BrowserRouter). Configure API CORS allowlists for the exact deployed frontend origin.

The current root Docker Compose frontend is a Vite development server and must not be used as the production static serving strategy. Bootstrap CSS/JS and icons are bundled from local npm dependencies, so the frontend does not depend on a runtime asset CDN.

## Backend and data requirements

Host Inventory API and Payment API as long-running ASGI services, plus both consumer workers. Provision reachable Redis and PostgreSQL services with persistence and backups. Configure service-to-service URLs and credentials through the hosting platform's secret/config mechanism. Do not use the `.env.example` password in production. Set `CORS_ORIGINS` to the specific frontend origin. Do not put server credentials in `VITE_*` variables.

Before public deployment, add authentication and authorization to administrative and order endpoints, validate inventory writes and order updates server-side, implement database schema migrations, define readiness/observability, and address cross-store event reliability (for example, transactional outbox/idempotency). Review Redis exposure and network policy. None of these are provided by this repository today.

## Netlify

No deployment was performed. A Netlify site/account authorization and independently hosted backend/data services are required before a functioning deployment can be built and verified. Once configured, verify deployed routes `/`, `/admin`, `/admin/create`, `/orders`, API CORS, browser console/network errors, and end-to-end order lifecycle against non-production data.
