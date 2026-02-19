# Herd

Multi-robot management server. FastAPI + WebSocket device communication. Python.

## Commands

- `make server` — start API server (port 8080, hot reload)
- `make test` — pytest
- `make check` — lint + type-check + test
- `make lint` / `make lint-fix` — ruff
- `make format` — ruff format
- `make simulate` — launch a simulated robot
- `make simulate-multi` — launch 3 simulated robots
- `make setup` — first-time setup (.env + dev deps)

## Architecture

`server/api/` — FastAPI HTTP endpoints
`server/simulation/` — simulated robot processes
`shared/` — types and utilities shared between server and clients
`clients/` — client implementations
`examples/` — runnable demos
`tests/` — pytest suite
