import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import database
import main
from routes_service import (
    RouteNotFoundError,
    RouteProviderError,
    RoutesApiKeyError,
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


class EventApiTest(unittest.TestCase):
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

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.database_path_patch.stop()
        self.temporary_directory.cleanup()

    def test_event_api_saves_and_updates_google_place_fields(self):
        create_data = {
            "title": "ハッカソン",
            "start_at": "2026-08-25T10:30",
            "end_at": "2026-08-25T17:30",
            "description": "",
            "location_name": "Garraway F",
            "destination": "福岡県福岡市中央区今泉1丁目19番22号",
            "destination_place_id": "ChIJ-created",
            "destination_lat": 33.586,
            "destination_lng": 130.398,
            "arrival_buffer_minutes": 10,
        }

        create_response = self.client.post("/api/events", json=create_data)

        self.assertEqual(create_response.status_code, 201)
        created_event = create_response.json()
        self.assertEqual(created_event["destination_place_id"], "ChIJ-created")
        self.assertEqual(created_event["destination_lat"], 33.586)
        self.assertEqual(created_event["destination_lng"], 130.398)
        self.assertEqual(self.client.get("/api/events").json(), [created_event])

        update_data = {
            **create_data,
            "location_name": "新しい会場",
            "destination": "新しい住所",
            "destination_place_id": "ChIJ-updated",
            "destination_lat": 33.59,
            "destination_lng": 130.4,
        }
        update_response = self.client.put(
            f"/api/events/{created_event['id']}",
            json=update_data,
        )

        self.assertEqual(update_response.status_code, 200)
        updated_event = update_response.json()
        self.assertEqual(updated_event["destination_place_id"], "ChIJ-updated")
        self.assertEqual(updated_event["destination_lat"], 33.59)
        self.assertEqual(updated_event["destination_lng"], 130.4)

    def test_event_api_allows_destination_without_google_place_fields(self):
        response = self.client.post(
            "/api/events",
            json={
                "title": "文字列だけの目的地",
                "start_at": "2026-08-25T10:30",
                "end_at": "2026-08-25T11:30",
                "destination": "天神駅の近く",
            },
        )

        self.assertEqual(response.status_code, 201)
        event = response.json()
        self.assertIsNone(event["destination_place_id"])
        self.assertIsNone(event["destination_lat"])
        self.assertIsNone(event["destination_lng"])


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
            destination="福岡県福岡市中央区今泉1丁目19番22号",
            destination_lat=33.586,
            destination_lng=130.398,
            arrival_buffer_minutes=10,
        )

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.database_path_patch.stop()
        self.temporary_directory.cleanup()

    def test_route_search_uses_place_coordinates_and_does_not_save(self):
        route_with_extra_fields = {
            **SAMPLE_ROUTE,
            "provider_response": {"ResultSet": {}},
            "segments": [
                {**segment, "provider_only_field": "フロントへ返さない"}
                for segment in SAMPLE_ROUTE["segments"]
            ],
        }

        with patch(
            "main.search_route",
            return_value=route_with_extra_fields,
        ) as search_route_mock:
            response = self.client.post(
                f"/api/events/{self.event['id']}/route-search",
                json={
                    "origin_name": "  九州大学 伊都キャンパス  ",
                    "origin_address": "福岡県福岡市西区元岡744",
                    "origin_place_id": "ChIJ-origin",
                    "origin_lat": 33.596,
                    "origin_lng": 130.215,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), SAMPLE_ROUTE)
        search_route_mock.assert_called_once_with(
            "33.596,130.215",
            "33.586,130.398",
            datetime(2026, 8, 24, 10, 20),
            origin_display_name="九州大学 伊都キャンパス",
            destination_display_name="Garraway F",
        )
        self.assertIsNone(database.get_travel_plan(self.event["id"]))

    def test_route_search_falls_back_to_addresses_and_names(self):
        address_event = database.create_event(
            "住所で検索する予定",
            "2026-08-24T11:00",
            "2026-08-24T12:00",
            location_name="表示用の会場名",
            destination="福岡市中央区の住所",
        )
        location_name_event = database.create_event(
            "名称で検索する予定",
            "2026-08-24T13:00",
            "2026-08-24T14:00",
            location_name="天神駅",
        )

        with patch("main.search_route", return_value=SAMPLE_ROUTE) as mock:
            address_response = self.client.post(
                f"/api/events/{address_event['id']}/route-search",
                json={
                    "origin_name": "九州大学",
                    "origin_address": "福岡市西区の住所",
                },
            )
            name_response = self.client.post(
                f"/api/events/{location_name_event['id']}/route-search",
                json={"origin_name": "博多駅"},
            )

        self.assertEqual(address_response.status_code, 200)
        self.assertEqual(name_response.status_code, 200)
        self.assertEqual(
            mock.call_args_list[0].args[:2],
            ("福岡市西区の住所", "福岡市中央区の住所"),
        )
        self.assertEqual(
            mock.call_args_list[0].kwargs,
            {
                "origin_display_name": "九州大学",
                "destination_display_name": "表示用の会場名",
            },
        )
        self.assertEqual(
            mock.call_args_list[1].args[:2],
            ("博多駅", "天神駅"),
        )

    def test_route_search_works_with_mock_provider_without_google_api(self):
        mock_event = database.create_event(
            "ハッカソン",
            "2026-08-25T10:22",
            "2026-08-25T18:00",
            location_name="Garraway F",
            destination_lat=33.586,
            destination_lng=130.398,
            arrival_buffer_minutes=10,
        )

        with patch.dict(os.environ, {"ROUTE_PROVIDER": "mock"}, clear=True):
            response = self.client.post(
                f"/api/events/{mock_event['id']}/route-search",
                json={
                    "origin_name": "九州大学 伊都キャンパス",
                    "origin_lat": 33.596,
                    "origin_lng": 130.215,
                },
            )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(route["origin"], "九州大学 伊都キャンパス")
        self.assertEqual(route["destination"], "Garraway F")
        self.assertEqual(route["arrival_at"], "2026-08-25T09:57")
        self.assertIsNone(database.get_travel_plan(mock_event["id"]))

    def test_direct_route_search_uses_event_data_without_database(self):
        with patch.dict(os.environ, {"ROUTE_PROVIDER": "mock"}, clear=True):
            response = self.client.post(
                "/api/route-search",
                json={
                    "origin_name": "九州大学 伊都キャンパス",
                    "origin_lat": 33.596,
                    "origin_lng": 130.215,
                    "event": {
                        "start_at": "2026-08-25T10:22",
                        "location_name": "Garraway F",
                        "destination_lat": 33.586,
                        "destination_lng": 130.398,
                        "arrival_buffer_minutes": 10,
                    },
                },
            )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(route["origin"], "九州大学 伊都キャンパス")
        self.assertEqual(route["destination"], "Garraway F")
        self.assertEqual(route["arrival_at"], "2026-08-25T09:57")

    def test_mock_route_search_applies_event_arrival_buffer(self):
        mock_event = database.create_event(
            "朝の予定",
            "2026-08-26T09:30",
            "2026-08-26T10:30",
            location_name="Garraway F",
            destination_lat=33.586,
            destination_lng=130.398,
            arrival_buffer_minutes=15,
        )

        with patch.dict(os.environ, {"ROUTE_PROVIDER": "mock"}, clear=True):
            response = self.client.post(
                f"/api/events/{mock_event['id']}/route-search",
                json={
                    "origin_name": "九州大学 伊都キャンパス",
                    "origin_lat": 33.596,
                    "origin_lng": 130.215,
                },
            )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(route["arrival_at"], "2026-08-26T09:00")
        self.assertEqual(route["departure_at"], "2026-08-26T07:57")

    def test_route_search_works_with_ekispert_provider(self):
        ekispert_event = database.create_event(
            "ハッカソン",
            "2026-08-25T10:22",
            "2026-08-25T18:00",
            location_name="Garraway F",
            destination_lat=33.586,
            destination_lng=130.398,
            arrival_buffer_minutes=10,
        )
        fixture_path = (
            Path(__file__).parent
            / "fixtures"
            / "ekispert_route_demo.json"
        )
        provider_response = Mock()
        provider_response.is_success = True
        provider_response.status_code = 200
        provider_response.json.return_value = json.loads(
            fixture_path.read_text(encoding="utf-8")
        )

        with (
            patch.dict(
                os.environ,
                {
                    "EKISPERT_API_KEY": "test-api-key",
                    "ROUTE_PROVIDER": "ekispert",
                },
                clear=True,
            ),
            patch(
                "route_providers.ekispert_provider.httpx.get",
                return_value=provider_response,
            ) as mock_get,
        ):
            response = self.client.post(
                f"/api/events/{ekispert_event['id']}/route-search",
                json={
                    "origin_name": "九州大学 伊都キャンパス",
                    "origin_lat": 33.596,
                    "origin_lng": 130.215,
                },
            )

        self.assertEqual(response.status_code, 200)
        route = response.json()
        self.assertEqual(route["origin"], "九州大学 伊都キャンパス")
        self.assertEqual(route["destination"], "Garraway F")
        self.assertEqual(route["arrival_at"], "2026-08-25T09:57")
        self.assertEqual(route["transport_mode"], "TRANSIT")
        mock_get.assert_called_once()
        self.assertIsNone(database.get_travel_plan(ekispert_event["id"]))

    def test_route_search_validates_event_origin_and_destination(self):
        missing_event_response = self.client.post(
            "/api/events/999/route-search",
            json={"origin_name": "博多駅"},
        )
        empty_origin_response = self.client.post(
            f"/api/events/{self.event['id']}/route-search",
            json={},
        )
        event_without_destination = database.create_event(
            "通常の予定",
            "2026-08-24T11:00",
            "2026-08-24T12:00",
        )
        missing_destination_response = self.client.post(
            f"/api/events/{event_without_destination['id']}/route-search",
            json={"origin_name": "博多駅"},
        )
        invalid_request_response = self.client.post(
            f"/api/events/{self.event['id']}/route-search",
            json={"origin_lat": "緯度ではない値", "origin_lng": 130.4},
        )

        self.assertEqual(missing_event_response.status_code, 404)
        self.assertEqual(empty_origin_response.status_code, 400)
        self.assertEqual(missing_destination_response.status_code, 400)
        self.assertEqual(invalid_request_response.status_code, 422)

    def test_route_search_converts_service_errors_to_http_errors(self):
        endpoint = f"/api/events/{self.event['id']}/route-search"

        error_cases = [
            (RouteNotFoundError("経路が見つかりませんでした"), 404),
            (RouteProviderError("接続できませんでした"), 502),
            (RoutesApiKeyError("APIキーがありません"), 500),
        ]
        for service_error, expected_status in error_cases:
            with self.subTest(expected_status=expected_status):
                with patch("main.search_route", side_effect=service_error):
                    response = self.client.post(
                        endpoint,
                        json={"origin_name": "博多駅"},
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
