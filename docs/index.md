# Tesla Smart Charger Documentation

Dynamic charging control for one or more Tesla vehicles, using the built-in
charger and the Tesla Fleet API.

## What is the Tesla Smart Charger?

Tesla Smart Charger is a Python application that dynamically controls the
charging of your Tesla vehicles based on your home's live power consumption.
It runs on a local server (such as a Raspberry Pi) and throttles charging when
your home approaches its circuit limit, so you never trip the main breaker.

**v2 highlights:**

- **Multi-vehicle** — manage several Teslas from one installation, each with its
  own charge limits and priority.
- **Guided onboarding** — a 10-step wizard (OAuth 2.0 + PKCE) replaces manual
  JSON editing; no `config.json` to hand-write.
- **React dashboard** — live status, per-vehicle controls, overload history, and
  settings.
- **Overload strategies** — reduce charging **proportionally** across vehicles
  or by **priority** order.
- **Solar surplus charging** — when your energy monitor reports a grid export,
  charging ramps up to absorb the surplus instead of selling it back; grid
  imports stay at a target level.

## Getting started

- New install → [Quick start](quick-start.md)
- Upgrading from v1 → [Migrating v1 → v2](migration.md)
