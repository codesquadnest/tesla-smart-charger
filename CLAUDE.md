# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.10+, FastAPI, uvicorn |
| Frontend | React 19, Vite, Tailwind CSS v4, React Router v7, TanStack Query v5 |
| Database | SQLite (via `sqlite3` stdlib) |
| Tesla API | Fleet API (Bearer token) + `tesla-http-proxy` sidecar (HTTPS + mTLS + VIN) |
| Energy Monitor | Shelly EM (`http://{host}/status/`) |
| Auth | HTTP Basic Auth (bcrypt) |
| Config | `config/system.json`, `config/vehicles.json` (JSON files, written by the onboarding wizard, mounted as a Docker volume) |

## Architecture

```
tesla-http-proxy (port 4443, TLS + mTLS)  ←  tesla-smart-charger (uvicorn)
                                                          │
        ┌─────────────────────────────────────────────────┤
        │                          │                      │
   Fleet API               Energy Monitor           Dashboard
   (Bearer token)          (Shelly EM HTTP)         (React SPA)
```

`tesla_smart_charger/__main__.py` is the composition root: it builds a single
`AppConfig` singleton, wires FastAPI routers, starts background cron threads via
the `lifespan` context manager, and serves the built React SPA from
`dashboard/dist/` (falling back to a legacy `tesla_smart_charger/website/`
static page, then a 503 telling you to build the dashboard). A catch-all route
serves `index.html` for client-side React Router paths, guarding against path
traversal outside `dashboard/dist/`.

Background threads (daemon, joined on shutdown via a shared `stop_event`):
- `tsc_token_cron_thread` (`cron/token_cron.py`) — always started; refreshes Tesla OAuth tokens.
- `tsc_energy_monitor_thread` (`cron/em_cron.py`) — only started when the `-m`/`--monitor` CLI flag is set (Docker's default CMD always passes it).

When the energy monitor cron detects consumption over `homeMaxAmps`, it calls
`overload_handler` directly (no internal HTTP round-trip); the legacy `GET
/overload` endpoint exists only for manual/back-compat triggering.

**Layout**: sticky sidebar (`w-60`) + `<main>` with `overflow-y-auto`
(scrollable). Sidebar rendered first in DOM, main after.

## Critical context

- **VIN is required** for proxy command URLs — `set_charge_amp_limit()` uses `self.vehicle.vin` (17 chars), not the numeric `teslaVehicleId`. The proxy validates VIN length and rejects Fleet API IDs with 404.
- **Tesla 109.0 firmware** blocks the partner-token vehicle data endpoint — `get_vehicle_data()` via Fleet API returns 408. A proxy-based data route may be needed as an alternative.
- **408 is expected** when the car is asleep — logged at `debug` level, no error surfaced to the dashboard.
- **Offline vehicle cache TTL**: 300s default, drops to 30s during an active overload session.
- **`telemetry_cache.invalidate()` bumps a per-vehicle generation counter**, and a refresh discards its result if the generation moved while it was in flight. Without this, a fetch started before a command lands after it and repopulates the cache with pre-command data for a full TTL. Any new code path that starts a refresh must carry the generation through — see `schedule_refresh`/`_refresh`.
- **Energy monitor IP validation**: `POST /api/v1/test-energy-monitor` rejects loopback, link-local, multicast, and reserved IPs.
- **OAuth flow**: redirect URI is `https://tesla.nalgascorp.org/done.html` (cannot change). A reverse proxy serves the static `done.html`. `/auth/start` uses POST (not GET) to avoid leaking `client_secret` in logs. If the reverse proxy serves a static page instead of forwarding the callback, the dashboard's Step 4 has a manual-paste fallback that extracts the OAuth code/issuer from a pasted URL.
- **Onboarding completion is all-or-nothing**: Step 10 only flips `configured: true` after system config, vehicles, and auth all save successfully — a partial failure does not mark the app configured, so a stale status cache (not a real failure) is the usual cause of the wizard looping back to Step 1.
- **`wake_up` goes direct to the Fleet API**, not through the proxy — waking needs no command signing, so it keeps working when the proxy is down. It uses the numeric `teslaVehicleId`; the VIN preference elsewhere exists only because the proxy rejects numeric ids on `/command/` paths.
- **`go install pkg@version` cannot build `teslamotors/vehicle-command`** — its `go.mod` has `replace` directives, which `go install` refuses. The Dockerfiles shallow-clone the pinned tag and `go build` from the module root instead. The version lives in `ARG VEHICLE_COMMAND_VERSION` (declared *inside* the builder stage — a pre-`FROM` ARG is out of scope after `FROM` and silently expands empty) and is overridable via `build.args` in `docker-compose.yaml`.
- **Basic Auth is enforced on `command_routes` only** — via `Depends(security.require_auth)` on the router. The guard **fails closed**: with auth unconfigured it returns 403, not open access. Everything else (`/api/v1/status`, vehicle CRUD, config, `/overload`) is still open to anyone who can reach port 8000, so put any new command with physical-world effects (unlock, trunk) on `command_routes`. `security.init(app_config)` must be wired before `status_routes` can report `authEnabled` — `__main__.py` does this, and tests must too.
- **The dashboard unlocks commands per tab** — `lib/authStore.ts` keeps `base64(user:pass)` in sessionStorage, `api/client.ts` attaches it as an `Authorization` header and clears it on any 401. `GET /api/v1/status` exposes `authEnabled` so the UI can lock the controls and explain why instead of firing requests that are guaranteed to fail.
- **Logging**: 10MB per file, 3 rotations (Docker logging driver `json-file`).
- **CORS**: wildcard origin (`*`) is incompatible with `allow_credentials=True` in browsers; credentials are only enabled when origins are explicitly listed (see `_cors_origins` handling in `__main__.py`).

## Conventions

- Python: ruff (`select = ["ALL"]`, line-length 88, target py310). See `pyproject.toml` for the ignore list. No comments on generated code unless essential.
- TypeScript: **single quotes, no semicolons**, 2-space indent (no Prettier is configured — match the surrounding files). `npx tsc --noEmit` must pass.
- React: function components, named exports, `interface Props` local to file, Tailwind classes inline.
- New components: look at existing ones for conventions first.
- Do **not** add comments to generated code.
- Do **not** commit unless explicitly asked.

## Dev commands

```sh
# Backend
uv run ruff check tesla_smart_charger tests                       # lint
uv run pytest                                                      # full test suite (cov gate: 80%)
uv run pytest tests/test_overload_handler.py                       # single test file
uv run pytest tests/test_overload_handler.py -k test_name          # single test
uv run tox                                                         # full matrix: py3.9-3.13 + lint + docs build

# Frontend (run from dashboard/)
npm install
npm run dev             # Vite dev server, http://localhost:5173, proxies /api,/auth,/overload to :8000
npx tsc --noEmit         # typecheck
npm run build            # tsc -b && vite build -> dashboard/dist/
npm run lint             # eslint .

# Running the backend directly (without Docker)
uv run tesla-smart-charger -m         # -m/--monitor enables the energy monitor cron
uv run tesla-smart-charger vehicles   # print Tesla vehicles for configured accounts and exit

# Docs
uv run mkdocs build      # or: uv run mkdocs serve
```

Local full-stack dev without Docker: run the backend (`uv run tesla-smart-charger -m`) and `cd dashboard && npm run dev` in separate terminals — no CORS config needed, Vite's dev proxy handles it. For Docker-based dev, copy `docker-compose.override.example.yml` to `docker-compose.override.yml` (git-ignored); it swaps in a live Vite server and puts `tesla-http-proxy` behind a `proxy` Compose profile so you can exercise onboarding Steps 1–4 without any certificates.

## Key files

| File | Purpose |
|---|---|
| `tesla_smart_charger/__main__.py` | App composition root: FastAPI app, lifespan/cron wiring, static SPA serving, CLI entry point |
| `tesla_smart_charger/app_config.py` | `AppConfig` — loads/persists `config/system.json` + vehicles |
| `tesla_smart_charger/tesla_api.py` | Tesla API client (Fleet API + proxy) |
| `tesla_smart_charger/handlers/overload_handler.py` | Overload detection + ramp-up/ramp-down logic |
| `tesla_smart_charger/cron/em_cron.py` | Energy monitor polling cron |
| `tesla_smart_charger/cron/token_cron.py` | OAuth token refresh cron |
| `tesla_smart_charger/telemetry_cache.py` | Per-vehicle telemetry cache (TTLs, background refresh, generation-guarded invalidation). Reads return copies — the cached instance is shared with the refresh thread |
| `tesla_smart_charger/routes/status_routes.py` | Status endpoint (reads the telemetry cache) |
| `tesla_smart_charger/routes/vehicle_routes.py` | Vehicle CRUD |
| `tesla_smart_charger/routes/command_routes.py` | Vehicle commands: wake, charge-limit, force-refresh (all behind `require_auth`) |
| `tesla_smart_charger/security.py` | Password hashing + the `require_auth` Basic Auth guard (fails closed) |
| `tesla_smart_charger/routes/auth_routes.py` | OAuth + Basic Auth routes |
| `tesla_smart_charger/routes/config_routes.py` | System config + `test-energy-monitor` |
| `tesla_smart_charger/models.py` | Pydantic models (`VehicleConfig`, `SystemConfig`) |
| `tesla_smart_charger/constants.py` | `CONFIG_DIR` (from `TESLA_CONFIG_DIR` env var) and other globals |
| `dashboard/src/components/layout/Sidebar.tsx` | Left sidebar navigation |
| `dashboard/src/components/layout/MainLayout.tsx` | Layout wrapper |
| `dashboard/src/pages/Settings/index.tsx` | Settings page (all 4 cards) |
| `dashboard/src/pages/Vehicles/index.tsx` | Vehicles list + add/edit forms |
| `dashboard/src/pages/Onboarding/steps/` | 10-step onboarding wizard |
| `docker-compose.yaml` | Services: `tesla-smart-charger` (app) + `tesla-http-proxy`. Keygen is not a service — `Dockerfile.tesla-keygen` is built on demand for cert generation |
| `docs/quick-start.md` | End-user setup guide + full settings reference — read this for onboarding/config semantics not covered above |
