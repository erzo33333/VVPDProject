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
    path('get_day_events/<int:year>/<int:month>/<int:day>/', views.get_day_events, name='get_day_events'),

    # Password Reset URLs (Django's built-in)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html', email_template_name='registration/password_reset_email.html', subject_template_name='registration/password_reset_subject.txt'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]