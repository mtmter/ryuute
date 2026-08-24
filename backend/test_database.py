import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


SAMPLE_TRAVEL_PLAN = {
    "origin": "博多駅",
    "destination": "福岡大学",
    "departure_at": "2026-08-24T12:52",
    "arrival_at": "2026-08-24T13:40",
    "duration_minutes": 48,
    "transport_mode": "TRANSIT",
    "route_details": json.dumps(
        {
            "segments": [
                {
                    "type": "TRANSIT",
                    "from": "博多駅",
                    "to": "福大前駅",
                    "departure_at": "2026-08-24T12:52",
                    "arrival_at": "2026-08-24T13:40",
                    "duration_minutes": 48,
                    "line_name": "福岡市地下鉄",
                }
            ]
        },
        ensure_ascii=False,
    ),
}


class TravelPlanDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "test_schedule.db"
        self.database_path_patch = patch.object(
            database,
            "DATABASE_PATH",
            database_path,
        )
        self.database_path_patch.start()
        database.initialize_database()

        self.event = database.create_event(
            "福岡大学でミーティング",
            "2026-08-24T14:00",
            "2026-08-24T15:00",
            location_name="福岡大学",
            destination="福岡県福岡市城南区七隈8-19-1",
            arrival_buffer_minutes=20,
        )

    def tearDown(self):
        self.database_path_patch.stop()
        self.temporary_directory.cleanup()

    def save_sample_travel_plan(self):
        return database.save_travel_plan(
            self.event["id"],
            SAMPLE_TRAVEL_PLAN["origin"],
            SAMPLE_TRAVEL_PLAN["destination"],
            SAMPLE_TRAVEL_PLAN["departure_at"],
            SAMPLE_TRAVEL_PLAN["arrival_at"],
            SAMPLE_TRAVEL_PLAN["duration_minutes"],
            SAMPLE_TRAVEL_PLAN["transport_mode"],
            SAMPLE_TRAVEL_PLAN["route_details"],
        )

    def test_new_table_has_required_origin_and_destination_columns(self):
        with database.connect_database() as connection:
            columns = {
                row["name"]: row
                for row in connection.execute(
                    "PRAGMA table_info(travel_plans)"
                ).fetchall()
            }

        self.assertEqual(columns["origin"]["notnull"], 1)
        self.assertEqual(columns["destination"]["notnull"], 1)

    def test_travel_plan_can_be_saved_and_retrieved(self):
        saved_travel_plan = self.save_sample_travel_plan()

        self.assertEqual(saved_travel_plan["event_id"], self.event["id"])
        self.assertEqual(
            saved_travel_plan["origin"],
            SAMPLE_TRAVEL_PLAN["origin"],
        )
        self.assertEqual(
            saved_travel_plan["destination"],
            SAMPLE_TRAVEL_PLAN["destination"],
        )
        self.assertEqual(
            json.loads(saved_travel_plan["route_details"])["segments"][0]["type"],
            "TRANSIT",
        )
        self.assertEqual(
            database.get_travel_plan(self.event["id"]),
            saved_travel_plan,
        )

    def test_resaving_replaces_the_existing_travel_plan(self):
        first_travel_plan = self.save_sample_travel_plan()

        replaced_travel_plan = database.save_travel_plan(
            self.event["id"],
            "天神駅",
            "福岡大学 七隈キャンパス",
            "2026-08-24T12:45",
            "2026-08-24T13:35",
            50,
            "TRANSIT",
            json.dumps({"segments": []}),
        )

        self.assertEqual(replaced_travel_plan["id"], first_travel_plan["id"])
        self.assertEqual(replaced_travel_plan["origin"], "天神駅")
        self.assertEqual(
            replaced_travel_plan["destination"],
            "福岡大学 七隈キャンパス",
        )
        self.assertEqual(
            replaced_travel_plan["departure_at"],
            "2026-08-24T12:45",
        )

        with database.connect_database() as connection:
            travel_plan_count = connection.execute(
                "SELECT COUNT(*) FROM travel_plans WHERE event_id = ?",
                (self.event["id"],),
            ).fetchone()[0]

        self.assertEqual(travel_plan_count, 1)

    def test_travel_plan_cannot_be_saved_for_missing_event(self):
        with self.assertRaises(sqlite3.IntegrityError):
            database.save_travel_plan(
                999,
                SAMPLE_TRAVEL_PLAN["origin"],
                SAMPLE_TRAVEL_PLAN["destination"],
                SAMPLE_TRAVEL_PLAN["departure_at"],
                SAMPLE_TRAVEL_PLAN["arrival_at"],
                SAMPLE_TRAVEL_PLAN["duration_minutes"],
                SAMPLE_TRAVEL_PLAN["transport_mode"],
                SAMPLE_TRAVEL_PLAN["route_details"],
            )

    def test_deleting_event_also_deletes_its_travel_plan(self):
        self.save_sample_travel_plan()

        database.delete_event(self.event["id"])

        self.assertIsNone(database.get_travel_plan(self.event["id"]))


class PreparationDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "test_schedule.db"
        self.database_path_patch = patch.object(
            database,
            "DATABASE_PATH",
            database_path,
        )
        self.database_path_patch.start()
        database.initialize_database()
        self.event = database.create_event(
            "成果物発表",
            "2026-08-24T14:00",
            "2026-08-24T15:00",
        )

    def tearDown(self):
        self.database_path_patch.stop()
        self.temporary_directory.cleanup()

    def test_preparations_can_be_created_loaded_updated_and_deleted(self):
        first_preparation = database.create_preparation(
            self.event["id"],
            "PCを充電する",
        )
        second_preparation = database.create_preparation(
            self.event["id"],
            "発表資料を提出する",
        )

        self.assertEqual(
            database.get_event_preparations(self.event["id"]),
            [first_preparation, second_preparation],
        )
        self.assertEqual(
            database.get_all_preparations(),
            [first_preparation, second_preparation],
        )

        updated_preparation = database.update_preparation(
            self.event["id"],
            first_preparation["id"],
            "PCとモバイルバッテリーを充電する",
            True,
        )
        self.assertEqual(
            updated_preparation["title"],
            "PCとモバイルバッテリーを充電する",
        )
        self.assertEqual(updated_preparation["completed"], 1)

        self.assertTrue(
            database.delete_preparation(
                self.event["id"],
                second_preparation["id"],
            )
        )
        self.assertEqual(
            database.get_event_preparations(self.event["id"]),
            [updated_preparation],
        )

    def test_preparation_must_belong_to_the_specified_event(self):
        other_event = database.create_event(
            "別の予定",
            "2026-08-24T16:00",
            "2026-08-24T17:00",
        )
        preparation = database.create_preparation(
            self.event["id"],
            "HDMI変換アダプターを持つ",
        )

        self.assertIsNone(
            database.update_preparation(
                other_event["id"],
                preparation["id"],
                preparation["title"],
                True,
            )
        )
        self.assertFalse(
            database.delete_preparation(
                other_event["id"],
                preparation["id"],
            )
        )

    def test_deleting_event_also_deletes_its_preparations(self):
        database.create_preparation(self.event["id"], "発表練習をする")

        database.delete_event(self.event["id"])

        self.assertEqual(database.get_event_preparations(self.event["id"]), [])

    def test_preparation_cannot_be_saved_for_missing_event(self):
        with self.assertRaises(sqlite3.IntegrityError):
            database.create_preparation(999, "存在しない予定の準備")


class TravelPlanMigrationTest(unittest.TestCase):
    def test_existing_travel_plan_is_kept_when_columns_are_added(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "old_schedule.db"

            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        start_at TEXT NOT NULL,
                        end_at TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        location_name TEXT,
                        destination TEXT,
                        arrival_buffer_minutes INTEGER
                    );

                    CREATE TABLE travel_plans (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL UNIQUE,
                        departure_at TEXT NOT NULL,
                        arrival_at TEXT NOT NULL,
                        duration_minutes INTEGER NOT NULL,
                        transport_mode TEXT NOT NULL,
                        route_details TEXT NOT NULL,
                        FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
                    );

                    INSERT INTO events (title, start_at, end_at)
                    VALUES ('既存の予定', '2026-08-24T14:00', '2026-08-24T15:00');

                    INSERT INTO travel_plans (
                        event_id,
                        departure_at,
                        arrival_at,
                        duration_minutes,
                        transport_mode,
                        route_details
                    )
                    VALUES (
                        1,
                        '2026-08-24T12:52',
                        '2026-08-24T13:40',
                        48,
                        'TRANSIT',
                        '{"segments": []}'
                    );
                    """
                )
            connection.close()

            with patch.object(database, "DATABASE_PATH", database_path):
                database.initialize_database()
                migrated_travel_plan = database.get_travel_plan(1)

                self.assertEqual(migrated_travel_plan["origin"], "")
                self.assertEqual(migrated_travel_plan["destination"], "")
                self.assertEqual(migrated_travel_plan["duration_minutes"], 48)
                self.assertEqual(database.get_all_events()[0]["title"], "既存の予定")

                created_task = database.create_task("移行後のタスク")
                self.assertEqual(created_task["title"], "移行後のタスク")


if __name__ == "__main__":
    unittest.main()
