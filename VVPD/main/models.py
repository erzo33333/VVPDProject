from django.db import models


class User(models.Model):
    Name = models.CharField(max_length=30, blank=False)
    Login = models.CharField(max_length=30, blank=False)
    Password = models.CharField(max_length=50, blank=False)
    Friends = models.ManyToManyField("self", symmetrical=True, blank=True)

    def __str__(self):
        return f'{self.Name} {self.id}'



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