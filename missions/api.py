from django_bolt import BoltAPI
from django_bolt.exceptions import NotFound

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
