from .database import CAPACITY_WATTS


def _row_to_dict(row):
    return dict(row)


def get_all_appliances(conn):
    rows = conn.execute("SELECT * FROM appliances ORDER BY id").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_current_load(conn):
    row = conn.execute(
        "SELECT COALESCE(SUM(wattage), 0) AS total FROM appliances WHERE state = 'running'"
    ).fetchone()
    return row["total"]


def log_event(conn, appliance_id, appliance_name, from_state, to_state, cause):
    conn.execute(
        """INSERT INTO event_log (appliance_id, appliance_name, from_state, to_state, cause)
           VALUES (?, ?, ?, ?, ?)""",
        (appliance_id, appliance_name, from_state, to_state, cause),
    )


def register_appliance(conn, name, wattage, priority):
    cur = conn.execute(
        "INSERT INTO appliances (name, wattage, priority, state) VALUES (?, ?, ?, 'off')",
        (name, wattage, priority),
    )
    appliance_id = cur.lastrowid
    log_event(conn, appliance_id, name, None, "off", "Registered")
    conn.commit()
    return appliance_id


def delete_appliance(conn, appliance_id):
    row = conn.execute("SELECT * FROM appliances WHERE id = ?", (appliance_id,)).fetchone()
    if row is None:
        return False, "Appliance not found"

    was_running = row["state"] == "running"
    conn.execute("DELETE FROM appliances WHERE id = ?", (appliance_id,))
    log_event(conn, appliance_id, row["name"], row["state"], "deleted", "Deleted by user")
    conn.commit()

    restored = attempt_restore(conn) if was_running else []
    return True, restored


def attempt_restore(conn):
    """
    Auto-restore policy (our choice, defended in the README):
    restore highest-priority (lowest priority number) shed appliances first;
    ties broken by whichever was registered first (id ascending). We loop
    repeatedly, because restoring one appliance may or may not leave enough
    room for the next-best candidate.
    """
    restored_names = []
    while True:
        load = get_current_load(conn)
        remaining = CAPACITY_WATTS - load
        candidate = conn.execute(
            """SELECT * FROM appliances
               WHERE state = 'shed' AND wattage <= ?
               ORDER BY priority ASC, id ASC
               LIMIT 1""",
            (remaining,),
        ).fetchone()
        if candidate is None:
            break
        conn.execute("UPDATE appliances SET state = 'running' WHERE id = ?", (candidate["id"],))
        log_event(
            conn, candidate["id"], candidate["name"], "shed", "running",
            "Auto-restored: capacity became available",
        )
        restored_names.append(candidate["name"])
    conn.commit()
    return restored_names


def turn_on(conn, appliance_id):
    row = conn.execute("SELECT * FROM appliances WHERE id = ?", (appliance_id,)).fetchone()
    if row is None:
        return False, "Appliance not found", [], []

    if row["state"] == "running":
        return True, f"{row['name']} is already running", [], []

    if row["state"] == "shed":
        # It's already "wanted on" and waiting for room; nothing to do.
        return True, f"{row['name']} is already waiting to be restored", [], []

    load = get_current_load(conn)
    remaining = CAPACITY_WATTS - load

    if row["wattage"] <= remaining:
        conn.execute("UPDATE appliances SET state = 'running' WHERE id = ?", (appliance_id,))
        log_event(conn, appliance_id, row["name"], "off", "running", "Turned on by user")
        conn.commit()
        return True, f"{row['name']} turned on", [], []

    # Not enough headroom - try to shed lower-priority (strictly higher
    # priority number) running appliances to make room.
    #
    # Shed order: among eligible candidates, we shed starting with the
    # lowest priority number first (the tier closest to the appliance being
    # turned on), escalating to less-important tiers only if that isn't
    # enough. This matches the spec's own worked example (turning on a
    # priority-1 appliance sheds only a priority-2 appliance when that alone
    # frees enough room, leaving a lower-priority-3 appliance untouched).
    deficit = row["wattage"] - remaining
    candidates = conn.execute(
        """SELECT * FROM appliances
           WHERE state = 'running' AND priority > ?
           ORDER BY priority ASC, wattage DESC, id ASC""",
        (row["priority"],),
    ).fetchall()

    to_shed = []
    freed = 0
    for c in candidates:
        if freed >= deficit:
            break
        to_shed.append(c)
        freed += c["wattage"]

    if freed < deficit:
        # Even shedding everything eligible isn't enough - reject and leave
        # state exactly as it was.
        return (
            False,
            f"Cannot turn on {row['name']}: not enough capacity even after "
            f"shedding all lower-priority appliances",
            [],
            [],
        )

    shed_names = []
    for c in to_shed:
        conn.execute("UPDATE appliances SET state = 'shed' WHERE id = ?", (c["id"],))
        log_event(
            conn, c["id"], c["name"], "running", "shed",
            f"Shed to make room for {row['name']}",
        )
        shed_names.append(c["name"])

    conn.execute("UPDATE appliances SET state = 'running' WHERE id = ?", (appliance_id,))
    log_event(conn, appliance_id, row["name"], "off", "running", "Turned on by user")
    conn.commit()

    message = f"{row['name']} turned on"
    if shed_names:
        message += f" -- shed to make room: {', '.join(shed_names)}"
    return True, message, shed_names, []


def turn_off(conn, appliance_id):
    row = conn.execute("SELECT * FROM appliances WHERE id = ?", (appliance_id,)).fetchone()
    if row is None:
        return False, "Appliance not found", []

    if row["state"] == "off":
        return True, f"{row['name']} is already off", []

    prev_state = row["state"]
    conn.execute("UPDATE appliances SET state = 'off' WHERE id = ?", (appliance_id,))

    if prev_state == "shed":
        # Explicitly turning off a shed appliance means the user no longer
        # wants it waiting - it stops being a restore candidate.
        cause = "Turned off by user while shed - stops waiting to auto-restore"
    else:
        cause = "Turned off by user"
    log_event(conn, appliance_id, row["name"], prev_state, "off", cause)
    conn.commit()

    restored = attempt_restore(conn) if prev_state == "running" else []

    message = f"{row['name']} turned off"
    if restored:
        message += f" -- restored: {', '.join(restored)}"
    return True, message, restored