from django.db import models



class Mission(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ABORTED = "aborted", "Aborted"
    class Clearance(models.TextChoices):
        TOP_SECRET = "top-secret", "Top Secret"
        CONFIDENTIAL = "confidential", "Confidential"

    name = models.CharField(max_length=100)
    status = models.CharField(max_length=100, default=Status.PLANNED, choices=Status.choices)
    launch_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    clearance = models.CharField(max_length=100, null=True, blank=True, choices=Clearance.choices)
    classified_data = models.CharField(max_length=255, null=True, blank=True)
    patch_image = models.CharField(max_length=255, blank=True) 

    def __str__(self):
        return self.name


class Astronaut(models.Model):
    class Role(models.TextChoices):
        COMMANDER = "commander", "Commander"
        SCIENTIST = "scientist", "Scientist"
        ENGINEER = "engineer", "Engineer"
        PILOT = "pilot", "Pilot"

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, default=Role.COMMANDER, choices=Role.choices)
    age = models.IntegerField(default=30)
    country = models.CharField(max_length=100)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="astronauts")

    def __str__(self):
        return f"{self.name} ({self.role})"