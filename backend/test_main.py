import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main
from routes_service import (
    RouteNotFoundError,
    RouteProviderError,
    RoutesApiKeyError,
)


ROUTE_REQUEST = {
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
}


def create_route_request(request_data=ROUTE_REQUEST):
    return main.DirectRouteSearchRequest.model_validate(request_data)


class HealthApiTest(unittest.TestCase):
    def test_health(self):
        self.assertEqual(main.health(), {"status": "ok"})

    def test_only_health_and_route_search_are_registered(self):
        api_routes = {
            (route.path, frozenset(route.methods or []))
            for route in main.app.routes
            if route.path.startswith("/api/")
        }

        self.assertEqual(
            api_routes,
            {
                ("/api/health", frozenset({"GET"})),
                ("/api/route-search", frozenset({"POST"})),
            },
        )


class RouteSearchApiTest(unittest.TestCase):
    def test_route_search_works_without_database(self):
        with patch.dict(
            os.environ,
            {"ROUTE_PROVIDER": "mock"},
            clear=True,
        ):
            route = main.search_direct_route(create_route_request())

        self.assertEqual(route["origin"], "九州大学 伊都キャンパス")
        self.assertEqual(route["destination"], "Garraway F")
        self.assertEqual(route["arrival_at"], "2026-08-25T09:57")
        self.assertEqual(route["transport_mode"], "TRANSIT")

    def test_route_search_validates_request(self):
        request_without_origin = {
            **ROUTE_REQUEST,
            "origin_name": "",
            "origin_lat": None,
            "origin_lng": None,
        }
        request_without_destination = {
            **ROUTE_REQUEST,
            "event": {
                "start_at": "2026-08-25T10:22",
            },
        }
        request_with_invalid_start = {
            **ROUTE_REQUEST,
            "event": {
                **ROUTE_REQUEST["event"],
                "start_at": "日時ではない値",
            },
        }

        for invalid_request in [
            request_without_origin,
            request_without_destination,
            request_with_invalid_start,
        ]:
            with self.subTest(invalid_request=invalid_request):
                with self.assertRaises(HTTPException) as context:
                    main.search_direct_route(
                        create_route_request(invalid_request),
                    )

                self.assertEqual(context.exception.status_code, 400)

    def test_route_search_converts_service_errors(self):
        error_cases = [
            (RouteNotFoundError("経路が見つかりませんでした"), 404),
            (RouteProviderError("接続できませんでした"), 502),
            (RoutesApiKeyError("APIキーがありません"), 500),
        ]

        for service_error, expected_status in error_cases:
            with self.subTest(expected_status=expected_status):
                with (
                    patch("main.search_route", side_effect=service_error),
                    self.assertRaises(HTTPException) as context,
                ):
                    main.search_direct_route(create_route_request())

                self.assertEqual(context.exception.status_code, expected_status)


if __name__ == "__main__":
    unittest.main()
