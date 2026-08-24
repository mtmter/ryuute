import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

import httpx

import routes_service
from route_providers import ekispert_provider


SAMPLE_GOOGLE_RESPONSE = {
    "routes": [
        {
            "duration": "3600s",
            "legs": [
                {
                    "steps": [
                        {
                            "staticDuration": "300s",
                            "travelMode": "WALK",
                        },
                        {
                            "staticDuration": "300s",
                            "travelMode": "WALK",
                        },
                        {
                            "staticDuration": "1800s",
                            "travelMode": "TRANSIT",
                            "transitDetails": {
                                "stopDetails": {
                                    "departureStop": {"name": "九大学研都市駅"},
                                    "departureTime": "2026-08-24T00:35:00Z",
                                    "arrivalStop": {"name": "天神駅"},
                                    "arrivalTime": "2026-08-24T01:05:00Z",
                                },
                                "transitLine": {
                                    "name": "JR筑肥線",
                                    "nameShort": "筑肥線",
                                },
                            },
                        },
                        {
                            "staticDuration": "900s",
                            "travelMode": "WALK",
                        },
                    ]
                }
            ],
        }
    ]
}


class EkispertRoutesServiceTest(unittest.TestCase):
    def create_success_response(self, response_data=None):
        response = Mock()
        response.is_success = True
        response.status_code = 200
        if response_data is None:
            fixture_path = (
                Path(__file__).parent
                / "fixtures"
                / "ekispert_route_demo.json"
            )
            response.json.return_value = json.loads(
                fixture_path.read_text(encoding="utf-8")
            )
        else:
            response.json.return_value = response_data
        return response

    def test_search_route_uses_mock_fixture_and_common_converter(self):
        result = routes_service.search_route(
            "33.596,130.215",
            "33.586,130.398",
            datetime(2026, 8, 25, 10, 12),
            provider_name="mock",
            origin_display_name="九州大学 伊都キャンパス",
            destination_display_name="Garraway F",
        )

        self.assertEqual(result["origin"], "九州大学 伊都キャンパス")
        self.assertEqual(result["destination"], "Garraway F")
        self.assertEqual(result["departure_at"], "2026-08-25T08:59")
        self.assertEqual(result["arrival_at"], "2026-08-25T10:12")
        self.assertEqual(result["duration_minutes"], 73)
        self.assertEqual(result["transport_mode"], "TRANSIT")
        self.assertEqual(
            [segment["type"] for segment in result["segments"]],
            ["WALK", "TRANSIT", "WALK"],
        )
        self.assertEqual(
            result["segments"][1]["line_name"],
            "JR筑肥線・福岡市地下鉄空港線",
        )

    def test_convert_ekispert_route_accepts_object_and_array_values(self):
        response_data = {
            "ResultSet": {
                "Course": [
                    {
                        "Route": {
                            "Line": {
                                "timeOnBoard": "7",
                                "Name": "JR中央線",
                                "Type": "train",
                                "DepartureState": {
                                    "Datetime": {
                                        "text": "2026-08-25T09:00:00+09:00"
                                    }
                                },
                                "ArrivalState": {
                                    "Datetime": {
                                        "text": "2026-08-25T09:07:00+09:00"
                                    }
                                },
                            },
                            "Point": [
                                {"Station": {"Name": "高円寺"}},
                                {"Station": {"Name": "新宿"}},
                            ],
                        }
                    }
                ]
            }
        }

        result = routes_service.convert_ekispert_route(
            response_data,
            "高円寺",
            "新宿",
        )

        self.assertEqual(result["duration_minutes"], 7)
        self.assertEqual(result["segments"][0]["type"], "TRANSIT")
        self.assertEqual(result["segments"][0]["line_name"], "JR中央線")

    def test_convert_ekispert_route_reports_missing_and_invalid_routes(self):
        with self.assertRaises(routes_service.RouteNotFoundError):
            routes_service.convert_ekispert_route(
                {"ResultSet": {}},
                "出発地",
                "目的地",
            )

        invalid_route = {
            "ResultSet": {
                "Course": {
                    "Route": {
                        "Line": {"Name": "徒歩", "Type": "walk"},
                        "Point": {"Name": "出発地"},
                    }
                }
            }
        }
        with self.assertRaises(routes_service.RoutesResponseError):
            routes_service.convert_ekispert_route(
                invalid_route,
                "出発地",
                "目的地",
            )

    def test_search_route_reports_unknown_provider(self):
        with self.assertRaises(routes_service.RouteProviderError):
            routes_service.search_route(
                "出発地",
                "目的地",
                datetime(2026, 8, 25, 10, 12),
                provider_name="unknown",
            )

    @patch("route_providers.ekispert_provider.httpx.get")
    def test_ekispert_provider_builds_arrival_search_query(self, mock_get):
        mock_get.return_value = self.create_success_response()

        response_data = ekispert_provider.get_route(
            "33.596,130.215",
            "33.586,130.398",
            datetime(2026, 8, 25, 1, 12, tzinfo=timezone.utc),
            api_key="test-api-key",
        )

        request_url = mock_get.call_args.args[0]
        query_string = urlsplit(request_url).query
        query_parameters = parse_qs(query_string)
        self.assertEqual(
            urlsplit(request_url).path,
            "/v1/json/search/course/extreme",
        )
        self.assertEqual(
            query_parameters,
            {
                "key": ["test-api-key"],
                "viaList": ["33.596,130.215:33.586,130.398"],
                "gcs": ["wgs84"],
                "date": ["20260825"],
                "time": ["1012"],
                "searchType": ["arrival"],
                "answerCount": ["1"],
                "sort": ["ekispert"],
            },
        )
        self.assertIn(":", query_string)
        self.assertNotIn("%3A", query_string)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 10.0)
        self.assertIn("ResultSet", response_data)

    def test_ekispert_provider_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ekispert_provider.EkispertApiKeyError):
                ekispert_provider.get_route(
                    "出発地",
                    "目的地",
                    datetime(2026, 8, 25, 10, 12),
                )

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(routes_service.RoutesApiKeyError):
                routes_service.search_route(
                    "出発地",
                    "目的地",
                    datetime(2026, 8, 25, 10, 12),
                    provider_name="ekispert",
                )

    @patch("route_providers.ekispert_provider.httpx.get")
    def test_ekispert_provider_reports_timeout_and_connection_errors(
        self,
        mock_get,
    ):
        error_cases = [
            httpx.TimeoutException("timeout"),
            httpx.RequestError("connection failed"),
        ]

        for request_error in error_cases:
            with self.subTest(error_type=type(request_error).__name__):
                mock_get.side_effect = request_error
                with self.assertRaises(
                    ekispert_provider.EkispertProviderError
                ):
                    ekispert_provider.get_route(
                        "出発地",
                        "目的地",
                        datetime(2026, 8, 25, 10, 12),
                        api_key="test-api-key",
                    )

    @patch("route_providers.ekispert_provider.httpx.get")
    def test_ekispert_provider_reports_http_and_json_errors(self, mock_get):
        for status_code in (400, 403, 500):
            with self.subTest(status_code=status_code):
                http_error_response = Mock()
                http_error_response.is_success = False
                http_error_response.status_code = status_code
                mock_get.return_value = http_error_response
                with self.assertRaises(
                    ekispert_provider.EkispertProviderError
                ):
                    ekispert_provider.get_route(
                        "出発地",
                        "目的地",
                        datetime(2026, 8, 25, 10, 12),
                        api_key="test-api-key",
                    )

        invalid_json_response = self.create_success_response()
        invalid_json_response.json.side_effect = ValueError("invalid json")
        mock_get.return_value = invalid_json_response

        with self.assertRaises(ekispert_provider.EkispertProviderError):
            ekispert_provider.get_route(
                "出発地",
                "目的地",
                datetime(2026, 8, 25, 10, 12),
                api_key="test-api-key",
            )

    @patch("route_providers.ekispert_provider.httpx.get")
    def test_search_route_uses_ekispert_provider_and_common_converter(
        self,
        mock_get,
    ):
        mock_get.return_value = self.create_success_response()

        with patch.dict(
            os.environ,
            {
                "EKISPERT_API_KEY": "test-api-key",
                "ROUTE_PROVIDER": "ekispert",
            },
            clear=True,
        ):
            result = routes_service.search_route(
                "33.596,130.215",
                "33.586,130.398",
                datetime(2026, 8, 25, 10, 12),
                origin_display_name="九州大学 伊都キャンパス",
                destination_display_name="Garraway F",
            )

        self.assertEqual(result["origin"], "九州大学 伊都キャンパス")
        self.assertEqual(result["destination"], "Garraway F")
        self.assertEqual(result["arrival_at"], "2026-08-25T10:12")
        self.assertEqual(result["transport_mode"], "TRANSIT")


class GoogleRoutesServiceTest(unittest.TestCase):
    def create_success_response(self, response_data=None):
        response = Mock()
        response.is_success = True
        response.status_code = 200
        response.json.return_value = response_data or SAMPLE_GOOGLE_RESPONSE
        return response

    @patch("routes_service.httpx.post")
    def test_search_route_sends_transit_request_and_converts_response(
        self,
        mock_post,
    ):
        mock_post.return_value = self.create_success_response()

        result = routes_service.search_google_route(
            "九州大学 伊都キャンパス",
            "Garraway F",
            datetime(2026, 8, 24, 10, 20),
            api_key="test-api-key",
        )

        request = mock_post.call_args
        self.assertEqual(request.args[0], routes_service.ROUTES_API_URL)
        self.assertEqual(request.kwargs["json"]["travelMode"], "TRANSIT")
        self.assertEqual(
            request.kwargs["json"]["arrivalTime"],
            "2026-08-24T01:20:00Z",
        )
        self.assertEqual(
            request.kwargs["headers"]["X-Goog-Api-Key"],
            "test-api-key",
        )

        self.assertEqual(result["departure_at"], "2026-08-24T09:20")
        self.assertEqual(result["arrival_at"], "2026-08-24T10:20")
        self.assertEqual(result["duration_minutes"], 60)
        self.assertEqual(result["transport_mode"], "TRANSIT")
        self.assertEqual(len(result["segments"]), 3)

        walk_segment = result["segments"][0]
        self.assertEqual(walk_segment["type"], "WALK")
        self.assertEqual(walk_segment["from"], "九州大学 伊都キャンパス")
        self.assertEqual(walk_segment["to"], "九大学研都市駅")
        self.assertEqual(walk_segment["departure_at"], "2026-08-24T09:20")
        self.assertEqual(walk_segment["arrival_at"], "2026-08-24T09:30")
        self.assertEqual(walk_segment["duration_minutes"], 10)

        transit_segment = result["segments"][1]
        self.assertEqual(transit_segment["type"], "TRANSIT")
        self.assertEqual(transit_segment["from"], "九大学研都市駅")
        self.assertEqual(transit_segment["to"], "天神駅")
        self.assertEqual(transit_segment["line_name"], "JR筑肥線")

        last_walk_segment = result["segments"][2]
        self.assertEqual(last_walk_segment["from"], "天神駅")
        self.assertEqual(last_walk_segment["to"], "Garraway F")
        self.assertEqual(last_walk_segment["arrival_at"], "2026-08-24T10:20")

    def test_convert_google_route_uses_desired_arrival_for_walk_only_route(self):
        response_data = {
            "routes": [
                {
                    "duration": "600s",
                    "legs": [
                        {
                            "steps": [
                                {
                                    "staticDuration": "600s",
                                    "travelMode": "WALK",
                                }
                            ]
                        }
                    ],
                }
            ]
        }

        result = routes_service.convert_google_route(
            response_data,
            "出発地",
            "目的地",
            datetime(2026, 8, 24, 10, 20),
        )

        self.assertEqual(result["departure_at"], "2026-08-24T10:10")
        self.assertEqual(result["arrival_at"], "2026-08-24T10:20")
        self.assertEqual(result["segments"][0]["from"], "出発地")
        self.assertEqual(result["segments"][0]["to"], "目的地")

    def test_search_route_raises_error_when_api_key_is_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(routes_service.RoutesApiKeyError):
                routes_service.search_google_route(
                    "出発地",
                    "目的地",
                    datetime(2026, 8, 24, 10, 20),
                )

    @patch("routes_service.httpx.post")
    def test_search_route_distinguishes_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("timeout")

        with self.assertRaises(routes_service.RoutesTimeoutError):
            routes_service.search_google_route(
                "出発地",
                "目的地",
                datetime(2026, 8, 24, 10, 20),
                api_key="test-api-key",
            )

    @patch("routes_service.httpx.post")
    def test_search_route_distinguishes_connection_error(self, mock_post):
        mock_post.side_effect = httpx.RequestError("connection failed")

        with self.assertRaises(routes_service.RoutesConnectionError):
            routes_service.search_google_route(
                "出発地",
                "目的地",
                datetime(2026, 8, 24, 10, 20),
                api_key="test-api-key",
            )

    @patch("routes_service.httpx.post")
    def test_search_route_distinguishes_google_error(self, mock_post):
        response = Mock()
        response.is_success = False
        response.status_code = 403
        response.json.return_value = {
            "error": {"message": "API key is not authorized"}
        }
        mock_post.return_value = response

        with self.assertRaises(routes_service.RoutesApiError) as context:
            routes_service.search_google_route(
                "出発地",
                "目的地",
                datetime(2026, 8, 24, 10, 20),
                api_key="test-api-key",
            )

        self.assertEqual(context.exception.status_code, 403)

    def test_convert_google_route_distinguishes_route_not_found(self):
        for response_data in ({}, {"routes": []}):
            with self.subTest(response_data=response_data):
                with self.assertRaises(routes_service.RouteNotFoundError):
                    routes_service.convert_google_route(
                        response_data,
                        "出発地",
                        "目的地",
                        datetime(2026, 8, 24, 10, 20),
                    )

    def test_convert_google_route_distinguishes_unexpected_response(self):
        unexpected_responses = [
            [],
            {"routes": "invalid"},
            {"routes": [{"duration": "600s"}]},
        ]

        for response_data in unexpected_responses:
            with self.subTest(response_data=response_data):
                with self.assertRaises(routes_service.RoutesResponseError):
                    routes_service.convert_google_route(
                        response_data,
                        "出発地",
                        "目的地",
                        datetime(2026, 8, 24, 10, 20),
                    )


if __name__ == "__main__":
    unittest.main()
