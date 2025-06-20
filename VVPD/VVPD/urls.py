"""
URL configuration for VVPD project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from main.views import main_page, index_page, second_page, user_login, register, user_logout, create_event, accept_friend_request, reject_friend_request,send_friend_request, friends_view, remove_friend, edit_event, delete_event, event_list


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('register/', register, name='register'),
    path('', main_page, name='main page'),
    path('index/', index_page),
    path('second/', second_page, name='second'),
    path('create-event/', create_event, name='create_event'),
    path('friends/accept/<int:user_id>/', accept_friend_request, name='accept_friend_request'),
    path('friends/reject/<int:user_id>/', reject_friend_request, name='reject_friend_request'),
    path('send_friend_request/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('friends/', friends_view, name='friends'),
    path('remove_friend/<int:user_id>/', remove_friend, name='remove_friend'),
    path('event/<int:event_id>/edit/', edit_event, name='edit_event'),
    path('event/<int:event_id>/delete/', delete_event, name='delete_event'),
    path('events/', event_list, name='event_list'),
]