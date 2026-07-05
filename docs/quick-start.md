# Quick start

This guide walks you through installing and configuring Tesla Smart Charger v2.

## Prerequisites

- Home server or Raspberry Pi with Git and Docker installed.
- Shelly EM (or compatible energy monitor).
- A public HTTPS endpoint you control for hosting the Tesla public key and OAuth
  callback URL (e.g. a subdomain served by Nginx).
- A Tesla developer account and a registered Tesla application.
- One or more Tesla vehicles.

---

## 1. Tesla developer setup

### 1.1 Create a Tesla application

1. Go to [developer.tesla.com](https://developer.tesla.com) and log in.
2. Create a new application. You will need:
   - A **public hostname** where you can host the public key and callback URL.
   - A **callback URL** in the form `https://<your-domain>/auth/callback`
     (this should point to your running tesla-smart-charger instance or a
     reverse-proxy in front of it).
3. Copy the **Client ID** — you will enter it in the onboarding wizard.
4. Copy the **Client Secret** — needed only for the partner registration step
   below.

### 1.2 Generate keys

Tesla Fleet API requires a signed ECDH key pair.  The private key stays on your
server; the public key must be reachable at:

```
https://<your-domain>/.well-known/appspecific/com.tesla.3p.public-key.pem
```

**Option A — using Go (tesla-keygen):**

```bash
git clone https://github.com/teslamotors/vehicle-command.git
cd vehicle-command/cmd/tesla-keygen
go build ./...
./tesla-keygen -key-file private-key.pem -keyring-type file -output public-key.pem create
```

**Option B — using Docker (no Go required):**

```bash
docker build -f Dockerfile.tesla-keygen -t tesla-keygen:latest .
docker run --rm -v "$PWD/certs:/app/certs" --name tesla-keygen tesla-keygen:latest
sudo chown $USER:$USER certs/*
```

Copy the generated files into the `certs/` directory at the project root.

### 1.3 Register your app with Tesla (one-time partner step)

Obtain a partner access token, then register your domain with the Fleet API.
Replace the placeholders below with your actual values.

```bash
# 1 — get a partner token
curl -s -X POST \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode 'scope=openid offline_access user_data vehicle_device_data vehicle_cmds vehicle_charging_cmds' \
  --data-urlencode "audience=https://fleet-api.prd.eu.vn.cloud.tesla.com" \
  'https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token' | jq -r .access_token

# 2 — register your domain
curl -s -X POST \
  -H "Authorization: Bearer $PARTNER_TOKEN" \
  -H 'Content-Type: application/json' \
  --data "{\"domain\": \"https://<your-domain>\"}" \
  https://fleet-api.prd.eu.vn.cloud.tesla.com/api/1/partner_accounts
```

> Change the Fleet API base URL for your region:
> - EU: `fleet-api.prd.eu.vn.cloud.tesla.com`
> - NA: `fleet-api.prd.na.vn.cloud.tesla.com`
> - AP: `fleet-api.prd.ap.vn.cloud.tesla.com`

### 1.4 Generate a TLS certificate for the HTTP proxy

The `tesla-http-proxy` sidecar needs a self-signed certificate.  Replace
`$PROXY_IP` with the LAN IP of your server.

```bash
export PROXY_IP=127.0.0.1

openssl req -x509 -nodes -newkey ec \
  -pkeyopt ec_paramgen_curve:secp521r1 \
  -pkeyopt ec_param_enc:named_curve \
  -subj '/CN=localhost' \
  -keyout certs/tls-key.pem \
  -out   certs/tls-cert.pem \
  -sha256 -days 3650 \
  -addext "subjectAltName = DNS:localhost, IP:$PROXY_IP" \
  -addext "extendedKeyUsage = serverAuth" \
  -addext "keyUsage = digitalSignature, keyCertSign, keyAgreement"
```

> Avoid the name `HTTPS_PROXY` here — it is a reserved environment variable that
> tools like `curl` interpret as a proxy to route requests through.

---

## 2. Start the stack

```bash
git clone https://github.com/codesquadnest/tesla-smart-charger.git
cd tesla-smart-charger

# Make sure certs/ contains: private-key.pem, public-key.pem, tls-key.pem, tls-cert.pem
docker compose up --build -d
```

The dashboard is served at `http://<server-ip>:8000`.

---

## 3. Onboarding wizard

On first access the dashboard displays a **10-step setup wizard**.  No manual
JSON editing is needed.

| Step | What you configure |
|------|-------------------|
| 1 — Welcome | Overview |
| 2 — Region & Voltage | Tesla Fleet API region (EU / NA / AP) and grid voltage |
| 3 — Tesla Application | Client ID, Client Secret, OAuth redirect URI, and HTTP proxy URL (where `tesla-http-proxy` is reachable) |
| 4 — Authorize | Opens Tesla sign-in in a popup; tokens are captured automatically. If your reverse proxy serves a static callback page instead of forwarding to the backend, paste the callback URL manually or use the hash-fallback method |
| 5 — Select Vehicles | Pick which vehicles from your Tesla account to manage |
| 6 — Charger Settings | Per-vehicle max/min charge amps |
| 7 — Energy Monitor | Shelly EM IP address and type — "Test connection" probes the device through the backend (no CORS issues) |
| 8 — Circuit & Strategy | Home circuit limit, overload strategy (proportional or priority) |
| 9 — Security | Optional HTTP Basic Auth for the dashboard |
| 10 — Done | Review and apply — config is written to `config/system.json` and `config/vehicles.json` |

After the wizard completes the application is fully operational.

---

## 4. Settings reference

These settings can be changed after onboarding via the dashboard **Settings** page (`GET /api/v1/config`) or directly in `config/system.json`.

### System

| Setting | Description |
|---------|-------------|
| `region` | Tesla Fleet API region: `eu`, `na`, or `ap`. Matches your vehicle's market. |
| `voltage` | Home grid voltage (V). Used to convert power (watts) to current (amps). |
| `hostIp` | IP address the API server binds to. |
| `apiPort` | TCP port the API server listens on. |

### Energy Monitor

| Setting | Description |
|---------|-------------|
| `energyMonitorType` | Hardware model. Currently only `shelly_em` is supported. |
| `energyMonitorIp` | IP address of the energy monitor on the local network. |

### Circuit & Strategy

| Setting | Description |
|---------|-------------|
| `homeMaxAmps` | Main breaker or circuit limit (A). Total consumption will not be allowed to exceed this. |
| `overloadStrategy` | How to distribute load reduction: `proportional` (all vehicles equally) or `priority` (lowest-priority vehicle first). |
| `sleepTimeSecs` | Seconds between adjustment steps during an overload event. Lower values react faster but may cause more API calls. |
| `downStepPercentage` | First-response factor when overload is detected (0.1–1.0). Current charge amps are multiplied by this (e.g. 0.5 = halve). |
| `upStepPercentage` | Factor used when ramping charge back up after overload clears (0.0–1.0). Applied to the amp range (max - min). |
| `maxSessionDuration` | Maximum seconds a supervised overload session can run before automatically ending. Prevents the car from staying stuck at a reduced limit. |

### Per-Vehicle (configured in `config/vehicles.json`)

| Setting | Description |
|---------|-------------|
| `chargerMaxAmps` | Maximum charging current (A) for this vehicle. The handler will not exceed this. |
| `chargerMinAmps` | Minimum charging current (A). The handler will not reduce below this. |
| `priority` | Overload priority (1 = highest). Higher numbers are reduced first in priority mode. |

### Security

| Setting | Description |
|---------|-------------|
| `auth.enabled` | Enable HTTP Basic Auth for the dashboard and API. |
| `auth.username` | Basic Auth username. |
| `auth.passwordHash` | Stored password hash (never returned by the API). |

---

## 5. Directory layout

```
tesla-smart-charger/
├── config/
│   ├── system.json     ← system-wide settings (written by wizard)
│   └── vehicles.json   ← per-vehicle credentials & settings (written by wizard)
├── data/               ← SQLite event database
└── certs/              ← TLS + vehicle command keys
```

These directories are mounted as Docker volumes so data survives container
rebuilds.

---

## 5. Running the energy monitor

The energy monitor (Shelly EM poller) is enabled by the `-m` / `--monitor` flag.

- **Docker:** it is **already enabled** — the image's default command is
  `tesla-smart-charger --monitor --verbose`, so no action is needed.
- **Running directly with `uv`:** pass the flag yourself:

  ```bash
  uv run tesla-smart-charger -m
  ```

When consumption exceeds `homeMaxAmps`, the monitor triggers overload handling
directly (throttling charging vehicles); no internal HTTP call is made.

---

## 6. Stopping the stack

```bash
docker compose down
```

---

## 7. Local development

A `docker-compose.override.example.yml` is included for rapid development.  It
replaces the static dashboard bundle with a live Vite dev server (port 5173)
and runs the Python backend with `--reload`.  Copy it to the (git-ignored)
`docker-compose.override.yml`, which Compose then merges automatically:

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
docker compose up       # backend + dashboard only — no certs needed
# Dashboard hot-reload: http://localhost:5173
# API:                  http://localhost:8000
```

The dev override puts `tesla-http-proxy` behind a **`proxy` profile**, so it is
**not started by default** — you can build the UI and walk through onboarding
Steps 1–4 with no certificates at all. When you need the proxy (Step 5 onward),
generate certs into `certs/` (see [§1.2](#12-generate-keys) and
[§1.4](#14-generate-a-tls-certificate-for-the-http-proxy)) and start it too:

```bash
docker compose --profile proxy up
```

> Requires Docker Compose ≥ 2.24 (for the `!reset` tag used to drop the proxy
> dependency in dev).

Or run the services separately without Docker:

```bash
# Terminal 1 — backend
uv run tesla-smart-charger -m

# Terminal 2 — dashboard
cd dashboard
npm install
npm run dev             # http://localhost:5173
```

Vite proxies `/api`, `/auth`, and `/overload` to the backend, so no CORS
configuration is needed during development. The proxy target defaults to
`http://localhost:8000` and can be overridden with the `VITE_API_PROXY_TARGET`
environment variable — the `docker-compose.override.yml` sets it to
`http://tesla-smart-charger:8000` so the dashboard container reaches the backend
container (inside Docker, `localhost` would point at the dashboard container
itself).

---

## 8. Troubleshooting

### `tesla-http-proxy` keeps restarting — `open /app/certs/private-key.pem: no such file or directory`

The proxy can't find its certificates. It needs **four** files in `certs/`:
`private-key.pem`, `public-key.pem` (see [§1.2](#12-generate-keys)) and
`tls-key.pem`, `tls-cert.pem` (see [§1.4](#14-generate-a-tls-certificate-for-the-http-proxy)).
Generate all four, then `docker compose up -d tesla-http-proxy`. Certificates are
**not** committed to the repo, so they must be generated on each host that runs
the stack.

In **dev**, you can avoid this entirely: the dev override keeps the proxy behind
the `proxy` profile, so `docker compose up` starts backend + dashboard only (no
certs needed). Add `--profile proxy` once you need the proxy — see
[§7](#7-local-development).

### Dashboard shows `502` / `/api/v1/status` fails, and onboarding "refreshes" every ~10s

The dashboard polls `GET /api/v1/status` every 10 seconds; a `502` means the
browser (or Vite's dev proxy) can't reach the backend on port `8000`.

- **Production:** confirm the `tesla-smart-charger` container is up and healthy
  (`docker compose ps`, `docker compose logs tesla-smart-charger`).
- **Dev (Vite in its own container):** ensure `VITE_API_PROXY_TARGET` points at
  the backend **service** (`http://tesla-smart-charger:8000`), not `localhost` —
  see [§7](#7-local-development). `localhost:8000` inside the dashboard container
  is the dashboard itself.

### `GET /` returns `503 — Dashboard not built`

The backend serves the compiled dashboard from `dashboard/dist/`. Build it
(`cd dashboard && npm install && npm run build`) or use Docker, which builds it
automatically. Without a build there is no SPA to serve.

### Onboarding never finishes / keeps returning to Step 1

Onboarding is only marked complete after **all** of Step 10's writes succeed
(system config → vehicles → auth → `configured: true`). If Step 10 shows an
error, fix that cause and re-apply — the app intentionally does not mark itself
configured on a partial save. A transient status-fetch failure alone no longer
forces you back into the wizard.

If clicking "Go to Dashboard" redirects back to `/onboarding`, the status query
may still return stale cached data. The fix awaits the refetch before navigating
— rebuild the dashboard image if you're on an older build.

### Authorisation popup shows a static page or "Not Found"

Your reverse proxy may serve a static file for the callback URL instead of
forwarding to the backend. When the popup cannot reach
`/auth/callback` on the backend, Step 4 provides a **manual paste** fallback:
copy the callback URL from the popup's address bar, paste it into the input
field, and click "Verify". The backend extracts the OAuth code and issuer
from the URL and completes the exchange.

### Tesla sign-in works but vehicle data / commands fail (proxy is up)

Getting tokens (Step 4) talks to Tesla directly, but reading vehicle data and
sending charge commands go through `tesla-http-proxy`, which requires your
**public key to be hosted** at
`https://<your-domain>/.well-known/appspecific/com.tesla.3p.public-key.pem` and
your **domain registered** with the Fleet API — see
[§1.2](#12-generate-keys) and [§1.3](#13-register-your-app-with-tesla-one-time-partner-step).
