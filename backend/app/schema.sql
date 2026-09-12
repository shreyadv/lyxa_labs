CREATE TABLE IF NOT EXISTS appliances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    wattage INTEGER NOT NULL CHECK (wattage > 0),
    priority INTEGER NOT NULL CHECK (priority >= 1),
    state TEXT NOT NULL CHECK (state IN ('running', 'off', 'shed')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Optional event log (stretch goal): records every state transition and why
-- it happened, e.g. "Fan shed to make room for Fridge".
CREATE TABLE IF NOT EXISTS event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    appliance_id INTEGER,
    appliance_name TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    cause TEXT NOT NULL
);
