from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from routes_service import (
    RouteNotFoundError,
    RoutesApiKeyError,
    RoutesServiceError,
    search_route,
)


app = FastAPI(title="Ryuute")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RouteSearchRequest(BaseModel):
    origin_name: str | None = None
    origin_address: str | None = None
    origin_place_id: str | None = None
    origin_lat: float | None = None
    origin_lng: float | None = None


class RouteSearchEvent(BaseModel):
    start_at: str
    location_name: str | None = None
    destination: str | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    arrival_buffer_minutes: int | None = None


class DirectRouteSearchRequest(RouteSearchRequest):
    event: RouteSearchEvent


class RouteSegment(BaseModel):
    type: str
    from_: str = Field(alias="from")
    to: str
    departure_at: str
    arrival_at: str
    duration_minutes: int = Field(ge=0)
    line_name: str | None = None


class RouteSearchResponse(BaseModel):
    origin: str
    destination: str
    departure_at: str
    arrival_at: str
    duration_minutes: int = Field(ge=0)
    transport_mode: str
    segments: list[RouteSegment]


def clean_optional_text(value):
    if value is None:
        return ""
    return value.strip()


def format_route_coordinates(latitude, longitude):
    if latitude is None or longitude is None:
        return ""
    return f"{latitude},{longitude}"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post(
    "/api/route-search",
    response_model=RouteSearchResponse,
)
def search_direct_route(request: DirectRouteSearchRequest):
    event = request.event
    origin_name = clean_optional_text(request.origin_name)
    origin_address = clean_optional_text(request.origin_address)
    origin_coordinates = format_route_coordinates(
        request.origin_lat,
        request.origin_lng,
    )
    origin = origin_coordinates or origin_address or origin_name
    if not origin:
        raise HTTPException(
            status_code=400,
            detail="出発地として利用できる情報を入力してください",
        )
    origin_display_name = origin_name or origin_address or origin

    destination_address = clean_optional_text(event.destination)
    destination_location_name = clean_optional_text(event.location_name)
    destination_coordinates = format_route_coordinates(
        event.destination_lat,
        event.destination_lng,
    )
    destination = (
        destination_coordinates
        or destination_address
        or destination_location_name
    )
    if not destination:
        raise HTTPException(status_code=400, detail="予定に目的地が設定されていません")
    destination_display_name = (
        destination_location_name or destination_address or destination
    )

    try:
        event_start = datetime.strptime(event.start_at, "%Y-%m-%dT%H:%M")
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="予定の開始日時が不正です",
        ) from error

    desired_arrival_at = event_start - timedelta(
        minutes=event.arrival_buffer_minutes or 0,
    )

    try:
        return search_route(
            origin,
            destination,
            desired_arrival_at,
            origin_display_name=origin_display_name,
            destination_display_name=destination_display_name,
        )
    except RouteNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RoutesApiKeyError as error:
        raise HTTPException(
            status_code=500,
            detail="経路検索のAPIキーが設定されていません",
        ) from error
    except RoutesServiceError as error:
        raise HTTPException(
            status_code=502,
            detail="経路検索サービスとの通信に失敗しました",
        ) from error
