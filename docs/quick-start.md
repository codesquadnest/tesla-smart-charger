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
`$HTTPS_PROXY` with the LAN IP of your server.

```bash
export HTTPS_PROXY=127.0.0.1

openssl req -x509 -nodes -newkey ec \
  -pkeyopt ec_paramgen_curve:secp521r1 \
  -pkeyopt ec_param_enc:named_curve \
  -subj '/CN=localhost' \
  -keyout certs/tls-key.pem \
  -out   certs/tls-cert.pem \
  -sha256 -days 3650 \
  -addext "subjectAltName = DNS:localhost, IP:$HTTPS_PROXY" \
  -addext "extendedKeyUsage = serverAuth" \
  -addext "keyUsage = digitalSignature, keyCertSign, keyAgreement"
```

---

## 2. Start the stack

```bash
git clone https://github.com/your-org/tesla-smart-charger.git
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
| 3 — Tesla Application | Client ID and HTTP proxy URL (where `tesla-http-proxy` is reachable) |
| 4 — Authorize | Opens Tesla sign-in in a popup; tokens are captured automatically |
| 5 — Select Vehicles | Pick which vehicles from your Tesla account to manage |
| 6 — Charger Settings | Per-vehicle max/min charge amps |
| 7 — Energy Monitor | Shelly EM IP address and type |
| 8 — Circuit & Strategy | Home circuit limit, overload strategy (proportional or priority) |
| 9 — Security | Optional HTTP Basic Auth for the dashboard |
| 10 — Done | Review and apply — config is written to `config/system.json` and `config/vehicles.json` |

After the wizard completes the application is fully operational.

---

## 4. Directory layout

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

The energy monitor (Shelly EM poller) is not started by default.  Pass the
`-m` flag to enable it:

```bash
# If running directly with uv
uv run tesla-smart-charger -m

# Or override the Docker command:
# In docker-compose.yaml, add to the tesla-smart-charger service:
#   command: ["python", "-m", "tesla_smart_charger", "-m"]
```

When consumption exceeds `homeMaxAmps` the monitor calls `GET /overload`
automatically.

---

## 6. Stopping the stack

```bash
docker compose down
```

---

## 7. Local development

A `docker-compose.override.yml` is included for rapid development.  It
replaces the static dashboard bundle with a live Vite dev server (port 5173)
and runs the Python backend with `--reload`:

```bash
docker compose up       # picks up the override automatically
# Dashboard hot-reload: http://localhost:5173
# API:                  http://localhost:8000
```

Or run the services separately without Docker:

```bash
# Terminal 1 — backend
uv run tesla-smart-charger -m

# Terminal 2 — dashboard
cd dashboard
npm install
npm run dev             # http://localhost:5173
```

Vite proxies `/api` and `/auth` to `http://localhost:8000`, so no CORS
configuration is needed during development.
