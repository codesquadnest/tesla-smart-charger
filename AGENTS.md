# Tesla Smart Charger v2

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.10+, FastAPI, uvicorn |
| Frontend | React 19, Vite, Tailwind CSS v4, React Router v7, TanStack Query v5 |
| Database | SQLite (via `sqlite3` stdlib) |
| Tesla API | Fleet API (Bearer token) + `tesla-http-proxy` (HTTPS + mTLS + VIN) |
| Energy Monitor | Shelly EM (`http://{host}/status/`) |
| Auth | HTTP Basic Auth (bcrypt) |
| Config | `config/system.json`, `config/vehicles/*.json` |

## Architecture

```
tesla-http-proxy (port 4443, TLS + mTLS)  ←  tesla-smart-charger (uvicorn)
                                                          │
        ┌─────────────────────────────────────────────────┤
        │                          │                      │
   Fleet API               Energy Monitor           Dashboard
   (Bearer token)          (Shelly EM HTTP)         (React SPA)
```

**Layout**: sticky sidebar (`w-60`) + `<main>` with `overflow-y-auto` (scrollable). Sidebar rendered first in DOM, main after.

## Critical Context

- **VIN is required** for proxy command URLs — `set_charge_amp_limit()` uses `self.vehicle.vin` (17 chars), not numeric `teslaVehicleId`. The proxy validates VIN length and rejects Fleet API IDs with 404.
- **Tesla 109.0 firmware** blocks the partner-token vehicle data endpoint — `get_vehicle_data()` via Fleet API returns 408. Proxy-based data route may be needed as alternative.
- **408 is expected** when car is asleep — logged at `debug` level, no error reported to dashboard.
- **Offline vehicle cache TTL**: 300s default, drops to 30s during active overload session.
- **Energy monitor IP validation**: `POST /api/v1/test-energy-monitor` rejects loopback, link-local, multicast, and reserved IPs.
- **OAuth flow**: redirect URI is `https://tesla.nalgascorp.org/done.html` (cannot change). Reverse proxy serves static `done.html`. `/auth/start` uses POST (not GET) to avoid leaking `client_secret` in logs.
- **Logging**: 10MB per file, 3 rotations (Docker logging driver `json-file`).
- **`--monitor` flag** enables the energy monitor cron (default in Docker CMD).

## Conventions

- Python: ruff (select ALL, line-length 88). No comments on code unless essential.
- TypeScript: double quotes, semicolons, `tabWidth: 2`. `npx tsc --noEmit` must pass.
- React: function components, named exports, `interface Props` local to file, Tailwind classes inline.
- New components: look at existing ones for conventions first.
- Do **not** add comments to generated code.
- Do **not** commit unless explicitly asked.

## Dev Commands

```sh
# Backend
uv run ruff check tesla_smart_charger tests          # lint
uv run pytest                                          # tests

# Frontend
cd dashboard && npx tsc --noEmit                       # typecheck
cd dashboard && npm run build                          # build
cd dashboard && npm run dev                            # dev server
```

## Key Files

| File | Purpose |
|---|---|
| `tesla_smart_charger/tesla_api.py` | Tesla API client (Fleet API + proxy) |
| `tesla_smart_charger/handlers/overload_handler.py` | Overload detection + ramp-up logic |
| `tesla_smart_charger/cron/em_cron.py` | Energy monitor polling cron |
| `tesla_smart_charger/routes/status_routes.py` | Status endpoint with cache TTL |
| `tesla_smart_charger/routes/vehicle_routes.py` | Vehicle CRUD |
| `tesla_smart_charger/routes/auth_routes.py` | OAuth + Basic Auth routes |
| `tesla_smart_charger/routes/config_routes.py` | System config + test-energy-monitor |
| `tesla_smart_charger/models.py` | Pydantic models (VehicleConfig, SystemConfig) |
| `tesla_smart_charger/constants.py` | CONFIG_DIR from TESLA_CONFIG_DIR env var |
| `dashboard/src/components/layout/Sidebar.tsx` | Left sidebar navigation |
| `dashboard/src/components/layout/MainLayout.tsx` | Layout wrapper |
| `dashboard/src/pages/Settings/index.tsx` | Settings page (all 4 cards) |
| `dashboard/src/pages/Vehicles/index.tsx` | Vehicles list + add/edit forms |
| `dashboard/src/pages/Onboarding/steps/` | Onboarding wizard steps |
| `dashboard/src/components/ui/InfoTooltip.tsx` | Info tooltip component |
| `docker-compose.yaml` | Services: app, proxy, keygen |
| `docs/quick-start.md` | User docs + settings reference |
