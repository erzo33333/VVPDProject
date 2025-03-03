from django.db import models


class User(models.Model):
    name = models.CharField(max_length=30, blank=False)
    login = models.CharField(max_length=30, blank=False)
    password = models.CharField(max_length=50, blank=False)
    EventsID = models.JSONField(null=True, blank=True, default=[])
    FriendsID = models.JSONField(null=True, blank=True, default=[])


class Event(models.Model):
    name = models.CharField(max_length=30, blank=False)
    creatorID = models.CharField(max_length=200)
    startTime = models.DateTimeField(blank=False)
    endTime = models.DateTimeField(blank=False)
    description = models.JSONField(null=True, blank=True, default=[])
    colour = models.CharField(max_length=20, blank=True, default='grey')
    participants = models.JSONField(blank=True, default=[]) #надо не забыть добавить метод добавления сюда creatorID при создании объекта