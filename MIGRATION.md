# Migrating from v1 to v2

This document is for users who were running **tesla-smart-charger v1** (single
vehicle, manual `config.json`) and want to upgrade to **v2** (multi-vehicle,
onboarding wizard, structured config).

---

## What changed

| Area | v1 | v2 |
|------|----|----|
| Configuration | Single flat `config.json` at project root | `config/system.json` + `config/vehicles.json` |
| Vehicles | One vehicle, hardcoded fields in `config.json` | Multiple vehicles, managed through the dashboard |
| OAuth | Manual `curl` token exchange | Built-in OAuth 2.0 + PKCE wizard (popup flow) |
| Dashboard | Basic status page | Full React SPA — Dashboard, Vehicles, History, Settings |
| Docker volumes | `./config.json:/app/config.json` bind-mount | `./config:/app/config` and `./data:/app/data` directories |
| Token refresh | Single cron job | Per-vehicle cron, one thread per vehicle |
| Overload strategy | Single vehicle, fixed downstep | Multi-vehicle: **proportional** or **priority** |

---

## Upgrade steps

### Step 1 — Back up your existing config

```bash
cp config.json config.json.v1.bak
```

### Step 2 — Update the repository

```bash
git pull origin main
```

### Step 3 — Update `docker-compose.yaml` volume mounts

v1 mapped a single file; v2 maps two directories.  Replace the old mount:

```yaml
# ❌ v1 — remove this
volumes:
  - ./config.json:/app/config.json
```

with the v2 mounts (already present if you pulled the updated
`docker-compose.yaml`):

```yaml
# ✅ v2
volumes:
  - ./config:/app/config
  - ./data:/app/data
  - ./certs:/app/certs:ro
```

### Step 4 — Rebuild and start

```bash
docker compose up --build -d
```

### What happens automatically on first start

When the application starts for the first time after the upgrade it looks for
`config.json` in the project root.  If found — and `config/system.json` does
not yet exist — it **automatically migrates** your settings:

- **System settings** (`homeMaxAmps`, `energyMonitorIp`, `sleepTimeSecs`,
  `downStepPercentage`, `upStepPercentage`, `hostIp`, `apiPort`) are written
  to `config/system.json`.
- **Vehicle credentials** (`teslaVehicleId`, `teslaAccessToken`,
  `teslaRefreshToken`, `teslaHttpProxy`, `teslaClientId`, `chargerMaxAmps`,
  `chargerMinAmps`) are written to `config/vehicles.json` as a single vehicle
  named "My Tesla".
- The system is marked as **already configured** so the onboarding wizard is
  not shown.

Migration is a **read-only** operation on `config.json` — the original file is
not deleted or modified.

### Step 5 — (Optional) Review migrated config in the dashboard

Open `http://<server-ip>:8000`.  You should land directly on the Dashboard
(not the wizard).  Navigate to **Vehicles** to rename your vehicle or adjust
charge limits, and to **Settings** to review all system parameters.

---

## Manual migration (if automatic migration fails)

If you prefer to migrate manually, or if the automatic migration produced
unexpected values:

1. Create the config directory:

   ```bash
   mkdir -p config
   ```

2. Write `config/system.json`:

   ```json
   {
     "homeMaxAmps": 30.0,
     "voltage": 230.0,
     "region": "eu",
     "energyMonitorIp": "YOUR_SHELLY_IP",
     "energyMonitorType": "shelly_em",
     "sleepTimeSecs": 30,
     "downStepPercentage": 0.5,
     "upStepPercentage": 0.25,
     "overloadStrategy": "proportional",
     "hostIp": "YOUR_SERVER_IP",
     "apiPort": 8000,
     "auth": { "enabled": false, "username": "", "passwordHash": "" },
     "configured": true
   }
   ```

3. Write `config/vehicles.json`:

   ```json
   [
     {
       "id": "generate-a-uuid-here",
       "name": "My Tesla",
       "vin": "",
       "teslaVehicleId": "YOUR_VEHICLE_ID",
       "teslaAccessToken": "YOUR_ACCESS_TOKEN",
       "teslaRefreshToken": "YOUR_REFRESH_TOKEN",
       "teslaHttpProxy": "http://tesla-http-proxy:4443",
       "teslaClientId": "YOUR_CLIENT_ID",
       "chargerMaxAmps": 25.0,
       "chargerMinAmps": 6.0,
       "priority": 1,
       "enabled": true
     }
   ]
   ```

   Generate a UUID with:

   ```bash
   python3 -c "import uuid; print(uuid.uuid4())"
   ```

4. Start the stack:

   ```bash
   docker compose up --build -d
   ```

---

## Adding more vehicles

After migration you have one vehicle.  To add more:

1. Open the dashboard at `http://<server-ip>:8000`.
2. Navigate to **Vehicles → Add vehicle**.
3. Enter the vehicle credentials (you can obtain a new OAuth token pair by
   clicking **Authorize with Tesla** — this opens the OAuth wizard popup and
   returns tokens for whichever account you log in with).

---

## Rollback

If you need to go back to v1:

```bash
git checkout v1   # or the last v1 tag
# Restore the docker-compose.yaml volume mounts
docker compose up --build -d
```

Your `config.json.v1.bak` can be restored with:

```bash
cp config.json.v1.bak config.json
```
