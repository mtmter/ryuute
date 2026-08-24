import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    create_event,
    create_preparation,
    create_task,
    delete_event,
    delete_preparation,
    delete_task,
    delete_travel_plan,
    get_all_events,
    get_all_preparations,
    get_all_tasks,
    get_event,
    get_event_preparations,
    get_travel_plan,
    initialize_database,
    save_travel_plan,
    update_event,
    update_preparation,
    update_task,
)
from routes_service import (
    RouteNotFoundError,
    RoutesApiKeyError,
    RoutesServiceError,
    search_route,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Ryuute", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


class EventCreate(BaseModel):
    title: str
    start_at: str
    end_at: str
    description: str = ""
    location_name: str | None = None
    destination: str | None = None
    destination_place_id: str | None = None
    destination_lat: float | None = None
    destination_lng: float | None = None
    arrival_buffer_minutes: int | None = None


class Event(BaseModel):
    id: int
    title: str
    start_at: str | None
    end_at: str | None
    description: str
    location_name: str | None
    destination: str | None
    destination_place_id: str | None
    destination_lat: float | None
    destination_lng: float | None
    arrival_buffer_minutes: int | None


class TaskCreate(BaseModel):
    title: str
    due_at: str | None = None
    description: str = ""


class TaskUpdate(BaseModel):
    title: str
    due_at: str | None
    description: str
    completed: bool


class Task(BaseModel):
    id: int
    title: str
    due_at: str | None
    description: str
    completed: bool


class PreparationCreate(BaseModel):
    title: str


class PreparationUpdate(BaseModel):
    title: str
    completed: bool


class Preparation(BaseModel):
    id: int
    event_id: int
    title: str
    completed: bool


class RouteSearchRequest(BaseModel):
    origin: str


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


class TravelPlanSave(RouteSearchResponse):
    pass


class TravelPlan(RouteSearchResponse):
    id: int
    event_id: int


def validate_event_times(start_at: str, end_at: str):
    try:
        start_datetime = datetime.strptime(start_at, "%Y-%m-%dT%H:%M")
        end_datetime = datetime.strptime(end_at, "%Y-%m-%dT%H:%M")
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="日時はYYYY-MM-DDTHH:mm形式で入力してください",
        ) from error

    if end_datetime < start_datetime:
        raise HTTPException(
            status_code=400,
            detail="終了日時は開始日時以降にしてください",
        )


def travel_plan_to_response(travel_plan):
    try:
        route_details = json.loads(travel_plan["route_details"])
        segments = route_details["segments"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail="保存された移動予定の経路情報が不正です",
        ) from error

    return {
        "id": travel_plan["id"],
        "event_id": travel_plan["event_id"],
        "origin": travel_plan["origin"],
        "destination": travel_plan["destination"],
        "departure_at": travel_plan["departure_at"],
        "arrival_at": travel_plan["arrival_at"],
        "duration_minutes": travel_plan["duration_minutes"],
        "transport_mode": travel_plan["transport_mode"],
        "segments": segments,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/events", response_model=list[Event])
def read_events():
    return get_all_events()


@app.post("/api/events", response_model=Event, status_code=status.HTTP_201_CREATED)
def add_event(event: EventCreate):
    title = event.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="予定タイトルを入力してください")

    validate_event_times(event.start_at, event.end_at)

    return create_event(
        title,
        event.start_at,
        event.end_at,
        event.description,
        event.location_name,
        event.destination,
        event.destination_place_id,
        event.destination_lat,
        event.destination_lng,
        event.arrival_buffer_minutes,
    )


@app.put("/api/events/{event_id}", response_model=Event)
def edit_event(event_id: int, event: EventCreate):
    title = event.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="予定タイトルを入力してください")

    validate_event_times(event.start_at, event.end_at)

    updated_event = update_event(
        event_id,
        title,
        event.start_at,
        event.end_at,
        event.description,
        event.location_name,
        event.destination,
        event.destination_place_id,
        event.destination_lat,
        event.destination_lng,
        event.arrival_buffer_minutes,
    )
    if updated_event is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    return updated_event


@app.delete("/api/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_event(event_id: int):
    if not delete_event(event_id):
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/events/{event_id}/route-search",
    response_model=RouteSearchResponse,
)
def search_event_route(event_id: int, request: RouteSearchRequest):
    event = get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    origin = request.origin.strip()
    if not origin:
        raise HTTPException(status_code=400, detail="出発地を入力してください")

    destination = (event["destination"] or "").strip()
    if not destination:
        raise HTTPException(status_code=400, detail="予定に目的地が設定されていません")

    try:
        event_start = datetime.strptime(event["start_at"], "%Y-%m-%dT%H:%M")
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail="予定の開始日時が不正です",
        ) from error

    arrival_buffer_minutes = event["arrival_buffer_minutes"] or 0
    desired_arrival_at = event_start - timedelta(
        minutes=arrival_buffer_minutes,
    )

    try:
        return search_route(origin, destination, desired_arrival_at)
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


@app.get(
    "/api/events/{event_id}/travel-plan",
    response_model=TravelPlan,
)
def read_travel_plan(event_id: int):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    travel_plan = get_travel_plan(event_id)
    if travel_plan is None:
        raise HTTPException(status_code=404, detail="移動予定が見つかりません")

    return travel_plan_to_response(travel_plan)


@app.put(
    "/api/events/{event_id}/travel-plan",
    response_model=TravelPlan,
)
def put_travel_plan(event_id: int, travel_plan: TravelPlanSave):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    route_details = json.dumps(
        {
            "segments": [
                segment.model_dump(by_alias=True)
                for segment in travel_plan.segments
            ]
        },
        ensure_ascii=False,
    )
    saved_travel_plan = save_travel_plan(
        event_id,
        travel_plan.origin,
        travel_plan.destination,
        travel_plan.departure_at,
        travel_plan.arrival_at,
        travel_plan.duration_minutes,
        travel_plan.transport_mode,
        route_details,
    )

    return travel_plan_to_response(saved_travel_plan)


@app.delete(
    "/api/events/{event_id}/travel-plan",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_travel_plan(event_id: int):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    if not delete_travel_plan(event_id):
        raise HTTPException(status_code=404, detail="移動予定が見つかりません")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/preparations", response_model=list[Preparation])
def read_preparations():
    return get_all_preparations()


@app.get(
    "/api/events/{event_id}/preparations",
    response_model=list[Preparation],
)
def read_event_preparations(event_id: int):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    return get_event_preparations(event_id)


@app.post(
    "/api/events/{event_id}/preparations",
    response_model=Preparation,
    status_code=status.HTTP_201_CREATED,
)
def add_preparation(event_id: int, preparation: PreparationCreate):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    title = preparation.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="準備項目名を入力してください")

    return create_preparation(event_id, title)


@app.put(
    "/api/events/{event_id}/preparations/{preparation_id}",
    response_model=Preparation,
)
def edit_preparation(
    event_id: int,
    preparation_id: int,
    preparation: PreparationUpdate,
):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    title = preparation.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="準備項目名を入力してください")

    updated_preparation = update_preparation(
        event_id,
        preparation_id,
        title,
        preparation.completed,
    )
    if updated_preparation is None:
        raise HTTPException(status_code=404, detail="準備項目が見つかりません")

    return updated_preparation


@app.delete(
    "/api/events/{event_id}/preparations/{preparation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_preparation(event_id: int, preparation_id: int):
    if get_event(event_id) is None:
        raise HTTPException(status_code=404, detail="予定が見つかりません")

    if not delete_preparation(event_id, preparation_id):
        raise HTTPException(status_code=404, detail="準備項目が見つかりません")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/tasks", response_model=list[Task])
def read_tasks():
    return get_all_tasks()


@app.post("/api/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def add_task(task: TaskCreate):
    title = task.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="タスクタイトルを入力してください")

    return create_task(title, task.due_at, task.description)


@app.put("/api/tasks/{task_id}", response_model=Task)
def edit_task(task_id: int, task: TaskUpdate):
    title = task.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="タスクタイトルを入力してください")

    updated_task = update_task(
        task_id,
        title,
        task.due_at,
        task.description,
        task.completed,
    )
    if updated_task is None:
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    return updated_task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_task(task_id: int):
    if not delete_task(task_id):
        raise HTTPException(status_code=404, detail="タスクが見つかりません")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
