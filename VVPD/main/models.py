from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    Friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    def __str__(self):
        return f'{self.username} {self.id}'


class Event(models.Model):
    Title = models.CharField(max_length=40, blank=False, default='event')
    CreatorID = models.CharField(max_length=200)
    StartTime = models.DateTimeField(blank=False)
    EndTime = models.DateTimeField(blank=False)
    Description = models.JSONField(null=True, blank=True, default=[])
    Colour = models.CharField(max_length=20, blank=True, default='grey')
    Participants = models.ManyToManyField(User, related_name="events")

    def __str__(self):
        return f'{self.Title} {self.id}'