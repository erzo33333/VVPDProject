from django.db import models


class User(models.Model):
    name = models.CharField(max_length=30, blank=False)
    login = models.CharField(max_length=30, blank=False)
    password = models.CharField(max_length=50, blank=False)
    EventsID = models.JSONField(null=True, blank=True, default=[])
    FriendsID = models.JSONField(null=True, blank=True, default=[])