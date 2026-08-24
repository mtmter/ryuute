import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("schedule.db")


@contextmanager
def connect_database():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    with connect_database() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                location_name TEXT,
                destination TEXT,
                destination_place_id TEXT,
                destination_lat REAL,
                destination_lng REAL,
                arrival_buffer_minutes INTEGER
            )
            """)

        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(events)").fetchall()
        }
        missing_columns = {
            "start_at": "TEXT",
            "end_at": "TEXT",
            "description": "TEXT NOT NULL DEFAULT ''",
            "location_name": "TEXT",
            "destination": "TEXT",
            "destination_place_id": "TEXT",
            "destination_lat": "REAL",
            "destination_lng": "REAL",
            "arrival_buffer_minutes": "INTEGER",
        }

        # CREATE TABLE IF NOT EXISTSだけでは既存テーブルに列が増えないため、
        # 保存済みの予定を残したまま不足している列だけを追加します。
        for column_name, column_definition in missing_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE events ADD COLUMN {column_name} {column_definition}"
                )

        # 以前のテーブルに残っている、現在使用しない列を削除します。
        for column_name in ("reflection", "created_at"):
            if column_name in existing_columns:
                connection.execute(f"ALTER TABLE events DROP COLUMN {column_name}")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS travel_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL UNIQUE,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_at TEXT NOT NULL,
                arrival_at TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                transport_mode TEXT NOT NULL,
                route_details TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )
            """
        )

        existing_travel_plan_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(travel_plans)"
            ).fetchall()
        }
        missing_travel_plan_columns = {
            "origin": "TEXT NOT NULL DEFAULT ''",
            "destination": "TEXT NOT NULL DEFAULT ''",
        }

        # 既存の移動予定には出発地・目的地が保存されていないため、
        # データを残したまま空文字の列を追加します。
        for column_name, column_definition in missing_travel_plan_columns.items():
            if column_name not in existing_travel_plan_columns:
                connection.execute(
                    "ALTER TABLE travel_plans "
                    f"ADD COLUMN {column_name} {column_definition}"
                )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_at TEXT,
                description TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS event_preparations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
            )
            """
        )


def get_all_events():
    with connect_database() as connection:
        rows = connection.execute("""
            SELECT
                id,
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes
            FROM events
            ORDER BY id
            """).fetchall()

    return [dict(row) for row in rows]


def get_event(event_id):
    with connect_database() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes
            FROM events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def create_event(
    title,
    start_at=None,
    end_at=None,
    description="",
    location_name=None,
    destination=None,
    destination_place_id=None,
    destination_lat=None,
    destination_lng=None,
    arrival_buffer_minutes=None,
):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            INSERT INTO events (
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes,
            ),
        )
        row = connection.execute(
            """
            SELECT
                id,
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes
            FROM events
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return dict(row)


def update_event(
    event_id,
    title,
    start_at=None,
    end_at=None,
    description="",
    location_name=None,
    destination=None,
    destination_place_id=None,
    destination_lat=None,
    destination_lng=None,
    arrival_buffer_minutes=None,
):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            UPDATE events
            SET
                title = ?,
                start_at = ?,
                end_at = ?,
                description = ?,
                location_name = ?,
                destination = ?,
                destination_place_id = ?,
                destination_lat = ?,
                destination_lng = ?,
                arrival_buffer_minutes = ?
            WHERE id = ?
            """,
            (
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes,
                event_id,
            ),
        )
        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            """
            SELECT
                id,
                title,
                start_at,
                end_at,
                description,
                location_name,
                destination,
                destination_place_id,
                destination_lat,
                destination_lng,
                arrival_buffer_minutes
            FROM events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

    return dict(row)


def delete_event(event_id):
    with connect_database() as connection:
        cursor = connection.execute(
            "DELETE FROM events WHERE id = ?",
            (event_id,),
        )

    return cursor.rowcount > 0


def get_travel_plan(event_id):
    with connect_database() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                event_id,
                origin,
                destination,
                departure_at,
                arrival_at,
                duration_minutes,
                transport_mode,
                route_details
            FROM travel_plans
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def save_travel_plan(
    event_id,
    origin,
    destination,
    departure_at,
    arrival_at,
    duration_minutes,
    transport_mode,
    route_details,
):
    with connect_database() as connection:
        connection.execute(
            """
            INSERT INTO travel_plans (
                event_id,
                origin,
                destination,
                departure_at,
                arrival_at,
                duration_minutes,
                transport_mode,
                route_details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                origin = excluded.origin,
                destination = excluded.destination,
                departure_at = excluded.departure_at,
                arrival_at = excluded.arrival_at,
                duration_minutes = excluded.duration_minutes,
                transport_mode = excluded.transport_mode,
                route_details = excluded.route_details
            """,
            (
                event_id,
                origin,
                destination,
                departure_at,
                arrival_at,
                duration_minutes,
                transport_mode,
                route_details,
            ),
        )
        row = connection.execute(
            """
            SELECT
                id,
                event_id,
                origin,
                destination,
                departure_at,
                arrival_at,
                duration_minutes,
                transport_mode,
                route_details
            FROM travel_plans
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()

    return dict(row)


def delete_travel_plan(event_id):
    with connect_database() as connection:
        cursor = connection.execute(
            "DELETE FROM travel_plans WHERE event_id = ?",
            (event_id,),
        )

    return cursor.rowcount > 0


def get_all_preparations():
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT id, event_id, title, completed
            FROM event_preparations
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_event_preparations(event_id):
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT id, event_id, title, completed
            FROM event_preparations
            WHERE event_id = ?
            ORDER BY id
            """,
            (event_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def create_preparation(event_id, title):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            INSERT INTO event_preparations (event_id, title)
            VALUES (?, ?)
            """,
            (event_id, title),
        )
        row = connection.execute(
            """
            SELECT id, event_id, title, completed
            FROM event_preparations
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return dict(row)


def update_preparation(event_id, preparation_id, title, completed):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            UPDATE event_preparations
            SET title = ?, completed = ?
            WHERE id = ? AND event_id = ?
            """,
            (title, completed, preparation_id, event_id),
        )
        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            """
            SELECT id, event_id, title, completed
            FROM event_preparations
            WHERE id = ?
            """,
            (preparation_id,),
        ).fetchone()

    return dict(row)


def delete_preparation(event_id, preparation_id):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            DELETE FROM event_preparations
            WHERE id = ? AND event_id = ?
            """,
            (preparation_id, event_id),
        )

    return cursor.rowcount > 0


def get_all_tasks():
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT id, title, due_at, description, completed
            FROM tasks
            ORDER BY id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def create_task(title, due_at=None, description=""):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (title, due_at, description)
            VALUES (?, ?, ?)
            """,
            (title, due_at, description),
        )
        row = connection.execute(
            """
            SELECT id, title, due_at, description, completed
            FROM tasks
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return dict(row)


def update_task(task_id, title, due_at, description, completed):
    with connect_database() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET title = ?, due_at = ?, description = ?, completed = ?
            WHERE id = ?
            """,
            (title, due_at, description, completed, task_id),
        )
        if cursor.rowcount == 0:
            return None

        row = connection.execute(
            """
            SELECT id, title, due_at, description, completed
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()

    return dict(row)


def delete_task(task_id):
    with connect_database() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )

    return cursor.rowcount > 0
