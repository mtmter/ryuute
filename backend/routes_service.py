import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

from route_providers import get_route_provider


ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
REQUEST_TIMEOUT_SECONDS = 10.0
JAPAN_TIMEZONE = timezone(timedelta(hours=9))
ROUTES_FIELD_MASK = ",".join(
    [
        "routes.duration",
        "routes.legs.steps.staticDuration",
        "routes.legs.steps.travelMode",
        "routes.legs.steps.transitDetails.stopDetails.departureStop.name",
        "routes.legs.steps.transitDetails.stopDetails.departureTime",
        "routes.legs.steps.transitDetails.stopDetails.arrivalStop.name",
        "routes.legs.steps.transitDetails.stopDetails.arrivalTime",
        "routes.legs.steps.transitDetails.transitLine.name",
        "routes.legs.steps.transitDetails.transitLine.nameShort",
    ]
)

load_dotenv(Path(__file__).with_name(".env"))

DEFAULT_ROUTE_PROVIDER = "mock"


class RoutesServiceError(Exception):
    """経路検索サービスで発生するエラーの基底クラス。"""


class RoutesApiKeyError(RoutesServiceError):
    """Google Maps APIキーが設定されていない。"""


class RoutesTimeoutError(RoutesServiceError):
    """Google Routes APIとの通信がタイムアウトした。"""


class RoutesConnectionError(RoutesServiceError):
    """Google Routes APIへ接続できなかった。"""


class RoutesApiError(RoutesServiceError):
    """Google Routes APIがエラーを返した。"""

    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


class RouteNotFoundError(RoutesServiceError):
    """条件に合う経路が見つからなかった。"""


class RoutesResponseError(RoutesServiceError):
    """外部サービスのレスポンスをアプリ用データへ変換できなかった。"""


class RouteProviderError(RoutesServiceError):
    """Route Providerの設定またはデータ取得に失敗した。"""


def search_route(origin, destination, arrival_at, provider_name=None):
    """設定されたProviderから駅すぱあと形式データを取得して変換する。"""
    selected_provider = (
        provider_name or os.getenv("ROUTE_PROVIDER", DEFAULT_ROUTE_PROVIDER)
    ).strip().lower()

    try:
        provider = get_route_provider(selected_provider)
        response_data = provider(origin, destination, arrival_at)
    except (OSError, ValueError, NotImplementedError) as error:
        raise RouteProviderError(str(error)) from error

    return convert_ekispert_route(response_data, origin, destination)


def convert_ekispert_route(response_data, origin, destination):
    """駅すぱあと形式のレスポンスをアプリ共通Route JSONへ変換する。"""
    if not isinstance(response_data, dict):
        raise RoutesResponseError(
            "駅すぱあとのレスポンスがJSONオブジェクトではありません"
        )

    result_set = response_data.get("ResultSet")
    if not isinstance(result_set, dict):
        raise RoutesResponseError(
            "駅すぱあとのレスポンスにResultSetがありません"
        )

    courses = as_list(result_set.get("Course"))
    if not courses:
        raise RouteNotFoundError("経路が見つかりませんでした")

    course = courses[0]
    if not isinstance(course, dict):
        raise RoutesResponseError("駅すぱあとのCourse形式が不正です")

    route = course.get("Route")
    if not isinstance(route, dict):
        raise RoutesResponseError("駅すぱあとのRoute形式が不正です")

    lines = as_list(route.get("Line"))
    points = as_list(route.get("Point"))
    if not lines:
        raise RoutesResponseError("駅すぱあとの経路に区間情報がありません")
    if len(points) != len(lines) + 1:
        raise RoutesResponseError(
            "駅すぱあとの経路で地点と区間の数が一致しません"
        )

    point_names = [_get_ekispert_point_name(point) for point in points]
    point_names[0] = origin
    point_names[-1] = destination

    segments = []
    for index, line in enumerate(lines):
        segments.append(
            _convert_ekispert_line(
                line,
                point_names[index],
                point_names[index + 1],
            )
        )

    departure_at = _parse_ekispert_datetime(
        lines[0],
        "DepartureState",
    )
    arrival_at = _parse_ekispert_datetime(lines[-1], "ArrivalState")
    duration_minutes = _datetime_duration_minutes(departure_at, arrival_at)

    return {
        "origin": origin,
        "destination": destination,
        "departure_at": _format_app_datetime(departure_at),
        "arrival_at": _format_app_datetime(arrival_at),
        "duration_minutes": duration_minutes,
        "transport_mode": (
            "TRANSIT"
            if any(segment["type"] == "TRANSIT" for segment in segments)
            else "WALK"
        ),
        "segments": segments,
    }


def as_list(value):
    """駅すぱあとJSONのobject / array差異をlistへそろえる。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _convert_ekispert_line(line, from_name, to_name):
    if not isinstance(line, dict):
        raise RoutesResponseError("駅すぱあとのLine形式が不正です")

    departure_at = _parse_ekispert_datetime(line, "DepartureState")
    arrival_at = _parse_ekispert_datetime(line, "ArrivalState")
    line_type = line.get("Type")
    line_name = line.get("Name")
    is_walk = (
        isinstance(line_type, str) and line_type.lower() == "walk"
    ) or line_name == "徒歩"

    if not is_walk and (not isinstance(line_name, str) or not line_name):
        raise RoutesResponseError("駅すぱあとの公共交通区間に路線名がありません")

    return {
        "type": "WALK" if is_walk else "TRANSIT",
        "from": from_name,
        "to": to_name,
        "departure_at": _format_app_datetime(departure_at),
        "arrival_at": _format_app_datetime(arrival_at),
        "duration_minutes": _datetime_duration_minutes(
            departure_at,
            arrival_at,
        ),
        "line_name": None if is_walk else line_name,
    }


def _get_ekispert_point_name(point):
    if not isinstance(point, dict):
        raise RoutesResponseError("駅すぱあとのPoint形式が不正です")

    name = point.get("Name")
    station = point.get("Station")
    if not name and isinstance(station, dict):
        name = station.get("Name")

    if not isinstance(name, str) or not name:
        raise RoutesResponseError("駅すぱあとのPointに地点名がありません")
    return name


def _parse_ekispert_datetime(line, state_name):
    try:
        datetime_value = line[state_name]["Datetime"]
        if isinstance(datetime_value, dict):
            datetime_value = datetime_value["text"]
        parsed_datetime = datetime.fromisoformat(datetime_value)
    except (KeyError, TypeError, ValueError) as error:
        raise RoutesResponseError(
            "駅すぱあとの区間に発着日時がありません"
        ) from error

    if parsed_datetime.tzinfo is None:
        raise RoutesResponseError("駅すぱあとの発着日時にタイムゾーンがありません")
    return parsed_datetime.astimezone(JAPAN_TIMEZONE)


def _datetime_duration_minutes(departure_at, arrival_at):
    duration_seconds = (arrival_at - departure_at).total_seconds()
    if duration_seconds < 0:
        raise RoutesResponseError("駅すぱあとの到着日時が出発日時より前です")
    return _seconds_to_minutes(duration_seconds)


def search_google_route(origin, destination, arrival_at, api_key=None):
    """Google Routes APIで公共交通の経路を1件検索する。"""
    google_api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
    if not google_api_key:
        raise RoutesApiKeyError("GOOGLE_MAPS_API_KEYが設定されていません")

    request_body = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "TRANSIT",
        "arrivalTime": _format_google_datetime(arrival_at),
        "computeAlternativeRoutes": False,
        "languageCode": "ja",
        "units": "METRIC",
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": ROUTES_FIELD_MASK,
    }

    try:
        response = httpx.post(
            ROUTES_API_URL,
            json=request_body,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as error:
        raise RoutesTimeoutError(
            "Google Routes APIとの通信がタイムアウトしました"
        ) from error
    except httpx.RequestError as error:
        raise RoutesConnectionError(
            "Google Routes APIへ接続できませんでした"
        ) from error

    if not response.is_success:
        message = _get_google_error_message(response)
        raise RoutesApiError(response.status_code, message)

    try:
        response_data = response.json()
    except ValueError as error:
        raise RoutesResponseError(
            "Google Routes APIのレスポンスがJSONではありません"
        ) from error

    return convert_google_route(
        response_data,
        origin,
        destination,
        arrival_at,
    )


def convert_google_route(response_data, origin, destination, desired_arrival_at):
    """Googleの生レスポンスから画面とDBで使う経路データだけを取り出す。"""
    if not isinstance(response_data, dict):
        raise RoutesResponseError("GoogleのレスポンスがJSONオブジェクトではありません")

    routes = response_data.get("routes")
    if routes is None or routes == []:
        raise RouteNotFoundError("経路が見つかりませんでした")
    if not isinstance(routes, list):
        raise RoutesResponseError("Googleのレスポンスのroutes形式が不正です")

    route = routes[0]
    try:
        total_duration_seconds = _parse_duration_seconds(route["duration"])
        raw_steps = [
            step
            for leg in route["legs"]
            for step in leg["steps"]
        ]
    except (KeyError, TypeError) as error:
        raise RoutesResponseError(
            "Googleのレスポンスに経路の時間または区間情報がありません"
        ) from error

    if not raw_steps:
        raise RoutesResponseError("Googleのレスポンスに経路の区間がありません")

    parsed_steps = _parse_steps(raw_steps)
    route_arrival = _calculate_route_arrival(
        parsed_steps,
        desired_arrival_at,
    )
    route_departure = route_arrival - timedelta(seconds=total_duration_seconds)
    _set_step_times(parsed_steps, route_departure)
    _set_step_places(parsed_steps, origin, destination)

    segments = []
    for step in parsed_steps:
        segments.append(
            {
                "type": step["type"],
                "from": step["from"],
                "to": step["to"],
                "departure_at": _format_app_datetime(step["departure_at"]),
                "arrival_at": _format_app_datetime(step["arrival_at"]),
                "duration_minutes": _seconds_to_minutes(
                    step["duration_seconds"]
                ),
                "line_name": step["line_name"],
            }
        )

    return {
        "origin": origin,
        "destination": destination,
        "departure_at": _format_app_datetime(route_departure),
        "arrival_at": _format_app_datetime(route_arrival),
        "duration_minutes": _seconds_to_minutes(total_duration_seconds),
        "transport_mode": "TRANSIT",
        "segments": segments,
    }


def _parse_steps(raw_steps):
    parsed_steps = []

    for raw_step in raw_steps:
        travel_mode = raw_step.get("travelMode")
        if not isinstance(travel_mode, str) or not travel_mode:
            raise RoutesResponseError(
                "Googleのレスポンスに区間の移動手段がありません"
            )

        try:
            duration_seconds = _parse_duration_seconds(
                raw_step["staticDuration"]
            )
        except KeyError as error:
            raise RoutesResponseError(
                "Googleのレスポンスに区間の所要時間がありません"
            ) from error

        if travel_mode == "TRANSIT":
            parsed_steps.append(
                _parse_transit_step(raw_step, duration_seconds)
            )
            continue

        # Googleが徒歩を複数の案内に分ける場合も、画面では1区間として扱います。
        if parsed_steps and parsed_steps[-1]["type"] == travel_mode:
            parsed_steps[-1]["duration_seconds"] += duration_seconds
            continue

        parsed_steps.append(
            {
                "type": travel_mode,
                "duration_seconds": duration_seconds,
                "departure_at": None,
                "arrival_at": None,
                "from": None,
                "to": None,
                "line_name": None,
            }
        )

    return parsed_steps


def _parse_transit_step(raw_step, duration_seconds):
    try:
        transit_details = raw_step["transitDetails"]
        stop_details = transit_details["stopDetails"]
        departure_at = _parse_google_datetime(stop_details["departureTime"])
        arrival_at = _parse_google_datetime(stop_details["arrivalTime"])
        departure_stop = stop_details["departureStop"]["name"]
        arrival_stop = stop_details["arrivalStop"]["name"]
    except (KeyError, TypeError, ValueError) as error:
        raise RoutesResponseError(
            "Googleのレスポンスに公共交通区間の情報が不足しています"
        ) from error

    transit_line = transit_details.get("transitLine", {})
    line_name = transit_line.get("name") or transit_line.get("nameShort")

    return {
        "type": "TRANSIT",
        "duration_seconds": duration_seconds,
        "departure_at": departure_at,
        "arrival_at": arrival_at,
        "from": departure_stop,
        "to": arrival_stop,
        "line_name": line_name,
    }


def _calculate_route_arrival(parsed_steps, desired_arrival_at):
    last_transit_index = None
    for index, step in enumerate(parsed_steps):
        if step["type"] == "TRANSIT":
            last_transit_index = index

    if last_transit_index is None:
        return _as_japan_datetime(desired_arrival_at)

    route_arrival = parsed_steps[last_transit_index]["arrival_at"]
    for step in parsed_steps[last_transit_index + 1 :]:
        route_arrival += timedelta(seconds=step["duration_seconds"])

    return route_arrival


def _set_step_times(parsed_steps, route_departure):
    first_transit_index = next(
        (
            index
            for index, step in enumerate(parsed_steps)
            if step["type"] == "TRANSIT"
        ),
        None,
    )

    if first_transit_index is None:
        current_time = route_departure
        for step in parsed_steps:
            step["departure_at"] = current_time
            current_time += timedelta(seconds=step["duration_seconds"])
            step["arrival_at"] = current_time
        return

    current_time = route_departure
    for index in range(first_transit_index):
        step = parsed_steps[index]
        step["departure_at"] = current_time
        current_time += timedelta(seconds=step["duration_seconds"])
        step["arrival_at"] = current_time

    for index in range(first_transit_index + 1, len(parsed_steps)):
        step = parsed_steps[index]
        if step["type"] == "TRANSIT":
            continue

        previous_arrival = parsed_steps[index - 1]["arrival_at"]
        step["departure_at"] = previous_arrival
        step["arrival_at"] = previous_arrival + timedelta(
            seconds=step["duration_seconds"]
        )


def _set_step_places(parsed_steps, origin, destination):
    for index, step in enumerate(parsed_steps):
        if step["type"] == "TRANSIT":
            continue

        previous_place = origin
        for previous_step in reversed(parsed_steps[:index]):
            if previous_step["to"]:
                previous_place = previous_step["to"]
                break

        next_place = destination
        for next_step in parsed_steps[index + 1 :]:
            if next_step["from"]:
                next_place = next_step["from"]
                break

        step["from"] = previous_place
        step["to"] = next_place


def _parse_duration_seconds(value):
    if not isinstance(value, str) or not value.endswith("s"):
        raise RoutesResponseError("Googleの所要時間の形式が不正です")

    try:
        seconds = float(value[:-1])
    except ValueError as error:
        raise RoutesResponseError("Googleの所要時間の形式が不正です") from error

    if seconds < 0:
        raise RoutesResponseError("Googleの所要時間が負の値です")

    return seconds


def _parse_google_datetime(value):
    if not isinstance(value, str):
        raise ValueError("Googleの日時が文字列ではありません")

    parsed_datetime = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed_datetime.tzinfo is None:
        raise ValueError("Googleの日時にタイムゾーンがありません")

    return parsed_datetime.astimezone(JAPAN_TIMEZONE)


def _as_japan_datetime(value):
    if not isinstance(value, datetime):
        raise RoutesResponseError("到着希望日時がdatetimeではありません")

    if value.tzinfo is None:
        return value.replace(tzinfo=JAPAN_TIMEZONE)

    return value.astimezone(JAPAN_TIMEZONE)


def _format_google_datetime(value):
    japan_datetime = _as_japan_datetime(value)
    utc_datetime = japan_datetime.astimezone(timezone.utc)
    return utc_datetime.isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_app_datetime(value):
    return value.astimezone(JAPAN_TIMEZONE).strftime("%Y-%m-%dT%H:%M")


def _seconds_to_minutes(seconds):
    return math.ceil(seconds / 60)


def _get_google_error_message(response):
    default_message = (
        f"Google Routes APIがエラーを返しました ({response.status_code})"
    )
    try:
        error_data = response.json()
    except ValueError:
        return default_message

    google_message = error_data.get("error", {}).get("message")
    if isinstance(google_message, str) and google_message:
        return google_message

    return default_message
