from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    Friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    def __str__(self):
        return f'{self.username} {self.id}'

    def create_event(self, title, start_time, end_time, description=None, colour='grey', participants=None):
        event = Event.objects.create(
            Title=title,
            Creator=self,
            StartTime=start_time,
            EndTime=end_time,
            Description=description if description is not None else [],
            Colour=colour,
        )
        event.Participants.add(self)
        if participants:
            event.Participants.add(*participants)
        return event

    def delete_event(self, event_id):
        try:
            event = Event.objects.get(id=event_id)
            if event.Creator != self:
                raise PermissionError("Вы не создатель события.")
            event.delete()
            return True
        except Event.DoesNotExist:
            raise ValueError("Такого события нет.")


class Event(models.Model):
    Title = models.CharField(max_length=40, blank=False, default='event')
    Creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    StartTime = models.DateTimeField(blank=False)
    EndTime = models.DateTimeField(blank=False)
    Description = models.JSONField(null=True, blank=True, default=[])
    Colour = models.CharField(max_length=20, blank=True, default='grey')
    Participants = models.ManyToManyField(User, related_name="events")

    def __str__(self):
        return f'{self.Title} {self.id}'