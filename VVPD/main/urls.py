from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('', views.main_page, name='main page'),
    path('second/', views.second_page, name='second'),
    path('create-event/', views.create_event, name='create_event'),
]