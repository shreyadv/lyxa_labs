# Inverter Load Manager

A small app that keeps a home inverter's load under 800W, automatically
shedding and restoring appliances by priority.

## How to run it

### Backend (FastAPI + SQLite)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
The SQLite file (`app/inverter.db`) is created automatically on first run.
API docs: http://localhost:8000/docs

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The frontend expects the backend at
`http://localhost:8000` (see `src/api.js`).

## Design notes

- **Modeling state:** each appliance has a single `state` column
  (`running` / `off` / `shed`) instead of separate booleans, so a row can
  never represent an invalid combination, and a server restart just reads
  this column straight back — no reconstruction needed.
- **Where the logic lives:** all shed/restore/on/off rules live in
  `backend/app/logic.py`, kept separate from the HTTP layer (`main.py`),
  which only translates results into responses and status codes.
- **Shed order:** when turning something on requires freeing capacity, we
  shed eligible running appliances (strictly lower priority than the one
  being turned on) starting with the tier closest in priority, escalating
  to less-important tiers only if that isn't enough. If shedding everything
  eligible still can't make room, the request is rejected and nothing
  changes.
- **Restore order:** we restore shed appliances by priority (most
  important first), ties broken by registration order. This favors
  bringing back the most critical appliance as soon as there's room,
  rather than restoring in the order things were shed — we felt that
  matched the spirit of "priority" better than a FIFO queue would.
- **Shed vs. off:** these are tracked as genuinely different states. A
  `shed` appliance is a restore candidate; an `off` appliance is not,
  even if a user switches off something that was previously shed.
- **Restart-proof:** because state lives entirely in SQLite and nothing is
  held in memory between requests, stopping and restarting the server
  requires no special handling — the database is the single source of
  truth.
- **One thing I'd change with more time:** add a dry-run/preview endpoint
  so the frontend could show "this will shed X and Y" before the user
  confirms turning something on, instead of finding out after the fact.

## API summary

| Method | Path                      | Description                                  |
|--------|---------------------------|-----------------------------------------------|
| GET    | `/status`                 | All appliances + current load + free capacity |
| GET    | `/appliances`             | List appliances                               |
| POST   | `/appliances`             | Register `{name, wattage, priority}`          |
| DELETE | `/appliances/{id}`        | Delete an appliance                           |
| POST   | `/appliances/{id}/on`     | Request ON                                    |
| POST   | `/appliances/{id}/off`    | Request OFF                                   |
| GET    | `/events`                 | Recent state-change history (stretch goal)    |

Rejections return `409` (can't fit) or `404` (not found) with a `detail`
explaining why, not a bare status code.
