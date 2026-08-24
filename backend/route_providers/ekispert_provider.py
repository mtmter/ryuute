import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx


EKISPERT_API_URL = (
    "https://api.ekispert.jp/v1/json/search/course/extreme"
)
REQUEST_TIMEOUT_SECONDS = 10.0
JAPAN_TIMEZONE = timezone(timedelta(hours=9))


class EkispertProviderError(Exception):
    """駅すぱあとAPIから経路を取得できなかった。"""


class EkispertApiKeyError(EkispertProviderError):
    """駅すぱあとAPIのアクセスキーが設定されていない。"""


def get_route(origin, destination, arrival_at, api_key=None):
    """駅すぱあとAPIで到着時刻を指定して経路を1件取得する。"""
    ekispert_api_key = api_key or os.getenv("EKISPERT_API_KEY")
    if not ekispert_api_key:
        raise EkispertApiKeyError("EKISPERT_API_KEYが設定されていません")

    arrival_datetime = _as_japan_datetime(arrival_at)
    query_parameters = {
        "key": ekispert_api_key,
        "viaList": f"{origin}:{destination}",
        "gcs": "wgs84",
        "date": arrival_datetime.strftime("%Y%m%d"),
        "time": arrival_datetime.strftime("%H%M"),
        "searchType": "arrival",
        "answerCount": "1",
        "sort": "ekispert",
    }
    # 駅すぱあとではviaListの区切り文字「:」をエンコードせず送ります。
    query_string = urlencode(query_parameters, safe=":,")
    request_url = f"{EKISPERT_API_URL}?{query_string}"

    try:
        response = httpx.get(
            request_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as error:
        raise EkispertProviderError(
            "駅すぱあとAPIとの通信がタイムアウトしました"
        ) from error
    except httpx.RequestError as error:
        raise EkispertProviderError(
            "駅すぱあとAPIへ接続できませんでした"
        ) from error

    if not response.is_success:
        raise EkispertProviderError(
            "駅すぱあとAPIがエラーを返しました "
            f"({response.status_code})"
        )

    try:
        response_data = response.json()
    except ValueError as error:
        raise EkispertProviderError(
            "駅すぱあとAPIのレスポンスがJSONではありません"
        ) from error

    if not isinstance(response_data, dict):
        raise EkispertProviderError(
            "駅すぱあとAPIのレスポンス形式が不正です"
        )

    return response_data


def _as_japan_datetime(value):
    if not isinstance(value, datetime):
        raise EkispertProviderError("到着希望日時がdatetimeではありません")

    if value.tzinfo is None:
        return value.replace(tzinfo=JAPAN_TIMEZONE)

    return value.astimezone(JAPAN_TIMEZONE)
