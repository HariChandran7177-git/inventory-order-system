# Testing and Quality Checks

## Executed results (2026-11-09)

| Check | Command | Result |
|---|---|---|
| Python unit, route, worker integration and e2e suite | `.venv\\Scripts\\python.exe -m pytest -q` | **64 passed in 2.03s**. Run had to execute outside the restricted sandbox because Windows `TestClient` socket-pair initialization hung inside it. |
| Frontend production bundle | `npm run build:frontend` | **Passed** with Vite 6.4.5; generated `frontend/dist` including locally bundled Bootstrap Icons fonts. |
| Frontend lint | `npm --workspace=frontend run lint` | **Passed**, no ESLint findings. |
| Frontend dependency advisory scan | `npm audit --workspace=frontend` | Initially 3 high severity React Router dependency advisories. `npm audit fix --workspace=frontend` applied compatible updates; output: **0 vulnerabilities**. |

The tests use in-memory Redis/PostgreSQL substitutes and ASGI test clients from `tests/conftest.py`; they verify application behavior but do not prove real Redis/PostgreSQL interoperability or a full browser workflow. No frontend component test runner or Playwright suite is configured.

## Coverage represented by the existing suite

- Inventory and payment route responses and CRUD paths.
- Inventory create/update validation for blank names and negative price/quantity (422).
- Fee calculation and order input/stock validation boundaries.
- Inventory caching and product feature behavior.
- Payment service behavior and health routes.
- Redis stream worker processing and cross-feature cases.
- End-to-end scenario tests for catalog browse, order placement, and simulated stock/order state progression.

## Repeat checks

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run build:frontend
npm --workspace=frontend run lint
npm audit --workspace=frontend
```

