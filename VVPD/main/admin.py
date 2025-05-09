from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from main.models import User, Event


admin.site.register(User, UserAdmin)   #почему-то не работает при разделении User и UserAdmin в разные строки
admin.site.register(Event)