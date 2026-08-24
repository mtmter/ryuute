import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "ekispert_route_demo.json"
)
JAPAN_TIMEZONE = timezone(timedelta(hours=9))

# このfixtureの基準検索条件として扱う到着希望日時です。
# 実APIのレスポンスへ差し替える場合は、取得時の検索条件に合わせます。
FIXTURE_DESIRED_ARRIVAL_AT = datetime(
    2026,
    8,
    25,
    10,
    12,
    tzinfo=JAPAN_TIMEZONE,
)


def get_route(_origin, _destination, arrival_at):
    """デモ用fixtureを到着希望日時に合わせて返す。"""
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        response_data = json.load(fixture_file)

    requested_arrival_at = _as_japan_datetime(arrival_at)
    time_difference = requested_arrival_at - FIXTURE_DESIRED_ARRIVAL_AT
    _shift_datetimes(response_data, time_difference)
    return response_data


def _as_japan_datetime(value):
    if not isinstance(value, datetime):
        raise ValueError("到着希望日時がdatetimeではありません")

    if value.tzinfo is None:
        return value.replace(tzinfo=JAPAN_TIMEZONE)

    return value.astimezone(JAPAN_TIMEZONE)


def _shift_datetimes(value, time_difference):
    """駅すぱあとJSON内のすべてのDatetimeを同じ差分だけ移動する。"""
    if isinstance(value, list):
        for item in value:
            _shift_datetimes(item, time_difference)
        return

    if not isinstance(value, dict):
        return

    datetime_value = value.get("Datetime")
    if isinstance(datetime_value, dict):
        datetime_text = datetime_value.get("text")
        if isinstance(datetime_text, str):
            parsed_datetime = datetime.fromisoformat(datetime_text)
            if parsed_datetime.tzinfo is None:
                raise ValueError("Mockの発着日時にタイムゾーンがありません")
            datetime_value["text"] = (
                parsed_datetime + time_difference
            ).isoformat()

    for child_value in value.values():
        _shift_datetimes(child_value, time_difference)
