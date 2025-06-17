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
    path('send_request/<int:user_id>/', views.send_friend_request, name='send_request'),
    path('accept_request/<int:user_id>/', views.accept_friend_request, name='accept_request'),
    path('reject_request/<int:user_id>/', views.reject_friend_request, name='reject_request'),
    path('friend_requests/', views.friend_requests_view, name='friend_requests'),
    path('send_friend_request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friends/', views.friends_view, name='friends'),
    path('remove_friend/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('event/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('events/', views.event_list, name='event_list'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
]