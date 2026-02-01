from datetime import datetime
from msgspec import Meta
from typing import Annotated, Literal

from django_bolt import BoltAPI
from django_bolt.exceptions import NotFound
from django_bolt.param_functions import Query
from django_bolt.serializers import Serializer, field_validator

from missions.models import Mission, Astronaut

api = BoltAPI()

# Basic endpoint
@api.get("/")
async def mission_control_status():
    return {
        "status": "operational",
        "message": "Mission Control is online"
    }

# Path parameters
@api.get("/missions/{mission_id}")
async def get_missions(mission_id: int):
    try:
        mission = await Mission.objects.aget(id=mission_id)
        return {
            "id": mission.id,
            "name": mission.name,
            "status": mission.status,
            "launch_date": str(mission.launch_date) if mission.launch_date else None,
            "description": mission.description,
        }
    except Mission.DoesNotExist:
        raise NotFound(detail=f"Mission {mission_id} not found")


@api.get("/astronauts/{astronaut_id}")
async def get_astronaut(astronaut_id: int):
    try:
        astronaut = await Astronaut.objects.aget(id=astronaut_id)
        return {
            "id": astronaut.id,
            "name": astronaut.name,
            "role": astronaut.role,
            "age": astronaut.age,
            "country": astronaut.country,
        }
    except Astronaut.DoesNotExist:
        raise NotFound(detail=f"Astronaut {astronaut_id} not found")


# Query parameters
class MissionFilters(Serializer):
    status: Literal["planned", "active", "completed", "aborted"] | None = None
    limit: Annotated[int, Meta(ge=1, le=100)] = 10
    launch_date: datetime | None = None


@api.get("/missions")
async def list_missions(filters: Annotated[MissionFilters, Query()]):
    queryset = Mission.objects.all()
    if filters.status:
        queryset = queryset.filter(status=filters.status)

    if filters.launch_date:
        queryset = queryset.filter(launch_date=filters.launch_date)
    
    missions = []
    async for mission in queryset[:filters.limit]:
        missions.append({
            "id": mission.id,
            "name": mission.name,
            "status": mission.status,
            "launch_date": str(mission.launch_date) if mission.launch_date else None,
        })
    return {
        "missions": missions,
        "count": len(missions),
    }
