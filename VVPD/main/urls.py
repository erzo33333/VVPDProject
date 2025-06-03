from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('create_event/', views.create_event, name='create_event'),
    path('get_month_events/<int:year>/<int:month>/', views.get_month_events, name='get_month_events'),
    path('get_event_details/<int:event_id>/', views.get_event_details, name='get_event_details'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('event/delete/<int:event_id>/', views.delete_event, name='delete_event'),
    path('get_day_events/<int:year>/<int:month>/<int:day>/', views.get_day_events, name='get_day_events'),

    # Friend System URLs
    path('users/', views.user_list, name='user_list'),
    path('send_friend_request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('friend_requests/', views.friend_requests, name='friend_requests'),
    path('accept_friend_request/<int:request_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('decline_friend_request/<int:request_id>/', views.decline_friend_request, name='decline_friend_request'),
    path('friends/', views.friend_list, name='friend_list'),
    path('remove_friend/<int:user_id>/', views.remove_friend, name='remove_friend'),

    # Chat System URLs
    path('chats/', views.chat_room_list, name='chat_room_list'),
    path('chat/<int:room_id>/', views.chat_room_detail, name='chat_room_detail'),
    path('chat/start/<int:user_id>/', views.start_or_get_chat, name='start_or_get_chat'),
    path('chat/<int:room_id>/send/', views.send_message, name='send_message'),

    # Password Reset URLs (Django's built-in)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html', email_template_name='registration/password_reset_email.html', subject_template_name='registration/password_reset_subject.txt'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    path('friend-requests-count-api/', views.friend_requests_count_api, name='friend_requests_count_api'),
    path('api/events_for_day/<str:date_str>/', views.api_events_for_day, name='api_events_for_day'),
    path('api/event_detail/<int:event_id>/', views.api_event_detail, name='api_event_detail'),
    path('friend-list-api/', views.friend_list_api, name='friend_list_api'),
    path('chat-room-list-api/', views.chat_room_list_api, name='chat_room_list_api'),
]