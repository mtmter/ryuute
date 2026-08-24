import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import database
import main
from routes_service import (
    RouteNotFoundError,
    RoutesApiKeyError,
    RoutesConnectionError,
)


SAMPLE_ROUTE = {
    "origin": "九州大学 伊都キャンパス",
    "destination": "Garraway F",
    "departure_at": "2026-08-24T09:20",
    "arrival_at": "2026-08-24T10:20",
    "duration_minutes": 60,
    "transport_mode": "TRANSIT",
    "segments": [
        {
            "type": "WALK",
            "from": "九州大学",
            "to": "九大学研都市駅",
            "departure_at": "2026-08-24T09:20",
            "arrival_at": "2026-08-24T09:30",
            "duration_minutes": 10,
            "line_name": None,
        },
        {
            "type": "TRANSIT",
            "from": "九大学研都市駅",
            "to": "天神駅",
            "departure_at": "2026-08-24T09:35",
            "arrival_at": "2026-08-24T10:05",
            "duration_minutes": 30,
            "line_name": "JR筑肥線",
        },
    ],
}


class RouteAndTravelPlanApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "test_schedule.db"
        self.database_path_patch = patch.object(
            database,
            "DATABASE_PATH",
            database_path,
        )
        self.database_path_patch.start()

        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()
        self.event = database.create_event(
            "ハッカソン",
            "2026-08-24T10:30",
            "2026-08-24T18:00",
            location_name="Garraway F",
            destination="Garraway F",
            arrival_buffer_minutes=10,
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.database_path_patch.stop()
        self.temporary_directory.cleanup()

    def test_route_search_uses_event_data_and_does_not_save(self):
        route_with_google_only_fields = {
            **SAMPLE_ROUTE,
            "raw_google_response": {"routes": ["生データ"]},
            "segments": [
                {**segment, "google_only_field": "フロントへ返さない"}
                for segment in SAMPLE_ROUTE["segments"]
            ],
        }

        with patch(
            "main.search_route",
            return_value=route_with_google_only_fields,
        ) as search_route_mock:
            response = self.client.post(
                f"/api/events/{self.event['id']}/route-search",
                json={"origin": "  九州大学 伊都キャンパス  "},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), SAMPLE_ROUTE)
        search_route_mock.assert_called_once_with(
            "九州大学 伊都キャンパス",
            "Garraway F",
            datetime(2026, 8, 24, 10, 20),
        )
        self.assertIsNone(database.get_travel_plan(self.event["id"]))

    def test_route_search_validates_event_origin_and_destination(self):
        missing_event_response = self.client.post(
            "/api/events/999/route-search",
            json={"origin": "博多駅"},
        )
        empty_origin_response = self.client.post(
            f"/api/events/{self.event['id']}/route-search",
            json={"origin": "   "},
        )
        event_without_destination = database.create_event(
            "通常の予定",
            "2026-08-24T11:00",
            "2026-08-24T12:00",
        )
        missing_destination_response = self.client.post(
            f"/api/events/{event_without_destination['id']}/route-search",
            json={"origin": "博多駅"},
        )

        self.assertEqual(missing_event_response.status_code, 404)
        self.assertEqual(empty_origin_response.status_code, 400)
        self.assertEqual(missing_destination_response.status_code, 400)

    def test_route_search_converts_service_errors_to_http_errors(self):
        endpoint = f"/api/events/{self.event['id']}/route-search"

        error_cases = [
            (RouteNotFoundError("経路が見つかりませんでした"), 404),
            (RoutesConnectionError("接続できませんでした"), 502),
            (RoutesApiKeyError("APIキーがありません"), 500),
        ]
        for service_error, expected_status in error_cases:
            with self.subTest(expected_status=expected_status):
                with patch("main.search_route", side_effect=service_error):
                    response = self.client.post(
                        endpoint,
                        json={"origin": "博多駅"},
                    )

                self.assertEqual(response.status_code, expected_status)
                self.assertIn("detail", response.json())

    def test_travel_plan_can_be_saved_loaded_replaced_and_deleted(self):
        endpoint = f"/api/events/{self.event['id']}/travel-plan"

        save_response = self.client.put(endpoint, json=SAMPLE_ROUTE)
        self.assertEqual(save_response.status_code, 200)
        saved_travel_plan = save_response.json()
        self.assertEqual(saved_travel_plan["event_id"], self.event["id"])
        self.assertEqual(saved_travel_plan["segments"], SAMPLE_ROUTE["segments"])
        self.assertNotIn("route_details", saved_travel_plan)

        database_travel_plan = database.get_travel_plan(self.event["id"])
        saved_route_details = json.loads(database_travel_plan["route_details"])
        self.assertEqual(saved_route_details["segments"], SAMPLE_ROUTE["segments"])

        get_response = self.client.get(endpoint)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json(), saved_travel_plan)

        replacement_route = {
            **SAMPLE_ROUTE,
            "origin": "博多駅",
            "duration_minutes": 50,
        }
        replace_response = self.client.put(endpoint, json=replacement_route)
        self.assertEqual(replace_response.status_code, 200)
        self.assertEqual(replace_response.json()["id"], saved_travel_plan["id"])
        self.assertEqual(replace_response.json()["origin"], "博多駅")

        delete_response = self.client.delete(endpoint)
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(self.client.get(endpoint).status_code, 404)

    def test_travel_plan_api_rejects_missing_event(self):
        endpoint = "/api/events/999/travel-plan"

        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(
            self.client.put(endpoint, json=SAMPLE_ROUTE).status_code,
            404,
        )
        self.assertEqual(self.client.delete(endpoint).status_code, 404)


class PreparationApiTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "test_schedule.db"
        self.database_path_patch = patch.object(
            database,
            "DATABASE_PATH",
            database_path,
        )
        self.database_path_patch.start()

        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()
        self.event = database.create_event(
            "成果物発表",
            "2026-08-24T14:00",
            "2026-08-24T15:00",
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.database_path_patch.stop()
        self.temporary_directory.cleanup()

    def test_preparation_api_supports_all_operations(self):
        event_endpoint = f"/api/events/{self.event['id']}/preparations"

        create_response = self.client.post(
            event_endpoint,
            json={"title": "  発表資料を提出する  "},
        )
        self.assertEqual(create_response.status_code, 201)
        created_preparation = create_response.json()
        self.assertEqual(created_preparation["title"], "発表資料を提出する")
        self.assertFalse(created_preparation["completed"])

        event_list_response = self.client.get(event_endpoint)
        self.assertEqual(event_list_response.status_code, 200)
        self.assertEqual(event_list_response.json(), [created_preparation])

        all_list_response = self.client.get("/api/preparations")
        self.assertEqual(all_list_response.status_code, 200)
        self.assertEqual(all_list_response.json(), [created_preparation])
        event_response = self.client.get("/api/events").json()[0]
        self.assertNotIn("preparations", event_response)

        item_endpoint = (
            f"{event_endpoint}/{created_preparation['id']}"
        )
        update_response = self.client.put(
            item_endpoint,
            json={
                "title": "発表資料を最終版へ更新する",
                "completed": True,
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            update_response.json()["title"],
            "発表資料を最終版へ更新する",
        )
        self.assertTrue(update_response.json()["completed"])

        delete_response = self.client.delete(item_endpoint)
        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(self.client.get(event_endpoint).json(), [])

    def test_preparation_api_validates_event_title_and_relationship(self):
        missing_event_endpoint = "/api/events/999/preparations"
        self.assertEqual(
            self.client.get(missing_event_endpoint).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                missing_event_endpoint,
                json={"title": "準備"},
            ).status_code,
            404,
        )

        event_endpoint = f"/api/events/{self.event['id']}/preparations"
        self.assertEqual(
            self.client.post(event_endpoint, json={"title": "   "}).status_code,
            400,
        )

        preparation = database.create_preparation(self.event["id"], "準備")
        preparation_endpoint = f"{event_endpoint}/{preparation['id']}"
        self.assertEqual(
            self.client.put(
                preparation_endpoint,
                json={"title": "   ", "completed": False},
            ).status_code,
            400,
        )
        other_event = database.create_event(
            "別の予定",
            "2026-08-24T16:00",
            "2026-08-24T17:00",
        )
        wrong_event_item_endpoint = (
            f"/api/events/{other_event['id']}/preparations/{preparation['id']}"
        )
        self.assertEqual(
            self.client.put(
                wrong_event_item_endpoint,
                json={"title": "準備", "completed": True},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(wrong_event_item_endpoint).status_code,
            404,
        )

    def test_deleting_event_removes_preparation(self):
        preparation = database.create_preparation(
            self.event["id"],
            "HDMI変換アダプターを持つ",
        )

        response = self.client.delete(f"/api/events/{self.event['id']}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(database.get_all_preparations(), [])
        item_endpoint = (
            f"/api/events/{self.event['id']}/preparations/{preparation['id']}"
        )
        self.assertEqual(self.client.delete(item_endpoint).status_code, 404)


if __name__ == "__main__":
    unittest.main()
