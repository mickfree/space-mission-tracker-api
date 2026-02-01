import os
from datetime import datetime
from msgspec import Meta
from typing import Annotated, Literal

from django_bolt import BoltAPI
from django_bolt.exceptions import NotFound, HTTPException
from django_bolt.param_functions import Query, Header, Form, File
from django_bolt.serializers import Serializer, field_validator
from django_bolt.responses import PlainText, HTML, Redirect
from django.template.loader import render_to_string

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
@api.get(
    "/missions/{mission_id}",
    summary="Get mission details",
    description="Retrieve detailed information about a specific space mission",
    tags=["missions"],
)
async def get_mission(mission_id: int):
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


# Request body validation
class CreateMission(Serializer):
    name: Annotated[str, Meta(min_length=1, max_length=100)]
    description: Annotated[str, Meta(max_length=500)] = ""
    launch_date: datetime | None = None

    @field_validator("name")
    def validate_name(cls, value):
        if value.lower().startswith("test"):
            raise ValueError("Mission name cannot start with 'test'")
        return value


@api.post("/missions")
async def create_mission(mission: CreateMission):
    mission = await Mission.objects.acreate(
        name=mission.name,
        description=mission.description,
        launch_date=mission.launch_date,
        status=Mission.Status.PLANNED,
    )
    return {
        "id": mission.id,
        "name": mission.name,
        "status": mission.status.value,
        "message": "Mission created successfully",
    }

# HTTP methods
class UpdateMission(Serializer):
    name: Annotated[str, Meta(min_length=1, max_length=100)] | None = None
    status: Literal["planned", "active", "completed", "aborted"] | None = None
    description: Annotated[str, Meta(max_length=500)] | None = None

@api.put("/missions/{mission_id}")
async def update_mission(mission_id: int, data: UpdateMission):
    try:
        mission = await Mission.objects.aget(id=mission_id)
    except Mission.DoesNotExist:
        raise NotFound(detail=f"Mission {mission_id} not found")

    mission.name = data.name if data.name is not None else mission.name
    mission.status = data.status if data.status is not None else mission.status
    mission.description = data.description if data.description is not None else mission.description

    await mission.asave()
    return {
        "id": mission.id,
        "name": mission.name,
        "status": mission.status,
        "description": mission.description,
    }
    
@api.delete("/missions/{mission_id}", status_code=204)
async def delete_mission(mission_id: int):
    try:
        mission = await Mission.objects.aget(id=mission_id)
    except Mission.DoesNotExist:
        raise NotFound(detail=f"Mission {mission_id} not found")
    
    await mission.adelete()


# Headers
@api.get("/missions/{mission_id}/classified")
async def get_classified_info(
    mission_id: int,
    clearance: Annotated[str, Header(alias="X-Clearance-Level")]
    ):
    if clearance not in Mission.Clearance.values:
        raise HTTPException(
            status_code=403,
            detail="Insufficient clearence level"
        )

    try: 
        mission = await Mission.objects.aget(id=mission_id)
    except Mission.DoesNotExist:
        raise NotFound(detail=f"Mission {mission_id} not found")

    return {
        "mission": mission.name,
        "classified_data": mission.classified_data,
        "clearance": clearance
    }

# Form data
class CreateAstronaut(Serializer):
    name: Annotated[str, Meta(min_length=1, max_length=100)]
    role: Annotated[str, Meta(min_length=1, max_length=20)]
    age: Annotated[int, Meta(ge=30, le=100)]
    country: Annotated[str, Meta(min_length=1, max_length=100)]

    @field_validator('role')
    def validate_role(cls, value):
        valid_roles = Astronaut.Role.values
        if value not in valid_roles:
            raise ValueError(f"Role Must be one of: {', '.join(valid_roles)}")
        return value


@api.post("/missions/{mission_id}/astronauts")
async def add_astronaut(
    mission_id: int,
    data: Annotated[CreateAstronaut, Form()]
):
    try:
        mission = await Mission.objects.aget(id=mission_id)
    except Mission.DoesNotExist:
        raise NotFound(detail=f"Mission {mission_id} not found")
    
    astronaut = await Astronaut.objects.acreate(
        name=data.name,
        role=data.role,
        age=data.age,
        country=data.country,
        mission=mission
    )

    return {
        "id": astronaut.id,
        "name": astronaut.name,
        "role": astronaut.role,
        "age": astronaut.age,
        "country": astronaut.country,
        "mission": mission.name
    }

# File Uploads
@api.post("/missions/{mission_id}/patch")
async def upload_mission_patch(
    mission_id: int,
    patch: Annotated[list[dict], File(alias="patch")]
):

    try:
        mission = await Mission.objects.aget(id=mission_id)
    except Mission.DoesNotExist:
        raise HTTPException(status_code=404, detail=f"mission {mission_id} not found")
    
    if not patch:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    file_info = patch[0]
    filename = file_info.get("filename", "patch.png")
    content = file_info.get("content", b"")
    size = file_info.get("size", 0)

    # save to media directory
    save_path = f"media/patches/{mission_id}_{filename}"
    os.makedirs("media/patches", exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(content)

    mission.patch_image = save_path
    await mission.asave()

    return {
        "message": "Mission patch uploaded successfully",
        "filename": filename,
        "size": size,
        "mission": mission.name 
    }


# Response types
@api.get("/missions/{mission_id}/log")
async def get_mission_log(mission_id: int):
    try:
        mission = await Mission.objects.aget(id=mission_id)
    except Mission.DoesNotExist:
        raise NotFound(detail=f"Mission {mission_id} not found")

    log = f"""
            === MISSION LOG: {mission.name} ===
            Status: {mission.status.upper()}
            Launch Date: {mission.launch_date or 'TBD'}
            Description: {mission.description or 'No description'}
            ================================
            """.strip()

    return PlainText(log)


# Django templates
@api.get("/status-page")
async def status_page():
    return HTML(render_to_string("status_page.html"))

@api.get("/go")
async def go_to_dashboard():
    return Redirect("/status-page")

@api.get("/dashboard")
async def dashboard():
    missions = []
    async for mission in Mission.objects.all()[:20]:
        missions.append({
            "name": mission.name,
            "status": mission.status,
            "description": mission.description
        })
    context = {
        "missions": missions
    }
    return HTML(render_to_string("dashboard.html", context))
