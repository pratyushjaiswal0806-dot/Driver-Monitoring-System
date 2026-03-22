# Driver Monitoring System

A React + Vite fleet dashboard for the Python driver monitoring backend. The backend reads alert records from SQLite and exposes REST endpoints for driver overview, alert history, health analysis, and analytics.

## Setup

1. Copy `alerts.db` from the Python project root into `fleet-dashboard/server/alerts.db`.
2. Run `npm install` from `fleet-dashboard/`.
3. Run `npm run dev` to start the Express API on `http://127.0.0.1:3001` and the Vite client on `http://127.0.0.1:5173`.

## Notes

- All alert records currently map to a single driver named `Default Driver`.
- This is intentionally hardcoded for Phase 1 and should be replaced once the database adds driver identity fields.
- The client uses polling every 5 seconds for the fleet overview.
- The dashboard does not include any live video feed. It only consumes the structured alert data already produced by the Python backend.

## Files

- `server/server.js` - Express REST API
- `server/db.js` - SQLite queries and aggregation helpers
- `client/` - React frontend
