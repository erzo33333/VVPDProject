from django.http import HttpResponse
from datetime import datetime
from main.models import User, Event
from django.shortcuts import render, redirect, get_object_or_404
from .forms import LoginForm, RegistrationForm, EventForm
from django.contrib import messages
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user is not None:
                login(request, user)
                return redirect('main page')
            else:
                return render(request, 'login.html', {'form': form, 'error': 'Неверные учетные данные'})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


@login_required(login_url='login')
def main_page(request):
    CurrentUser = request.user
    CurrentUserEvents = CurrentUser.events.all()
    friends = request.user.Friends.all()
    all_users = [CurrentUser] + list(friends)
    schedules = {}
    for u in all_users:
        events = Event.objects.filter(Creator=u)
        enriched_events = []
        for e in events:
            start_minutes = e.StartTime.hour * 60 + e.StartTime.minute
            end_minutes = e.EndTime.hour * 60 + e.EndTime.minute
            total_minutes = 24 * 60  # сутки

            left = ((start_minutes - 360) / total_minutes) * 100  # 6:00 — начало шкалы
            width = ((end_minutes - start_minutes) / total_minutes) * 100

            enriched_events.append({
                "Title": e.Title,
                "StartTime": e.StartTime,
                "EndTime": e.EndTime,
                "left": left,
                "width": width,
            })

        schedules[u.id] = enriched_events
    return render(request, 'MainPage.html', context={
        'events': CurrentUserEvents,
        'friends': friends,
        'schedules': schedules
    })


@login_required(login_url='login')
def index_page(request):
    return render(request, 'IndexPage.html', context={})


#@login_required(login_url='login')
def second_page(request):
    CurrentUser = request.user
    #CurrentUser.create_event('Велогонка', datetime(2025, 7, 5, 14, 30), datetime(2025, 7, 5, 17, 00), description=None, colour='green', participants=None)  #Создание ивента текущим пользователем
    #CurrentUser.Friends.add(User.objects.get(id=7))
    print(CurrentUser.username, CurrentUser.Friends.all())
    return render(request, 'SecondPage.html', context={})




@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.Creator = request.user
            if event.StartTime >= event.EndTime:
                messages.error(request, 'Ошибка: время окончания должно быть ПОЗЖЕ времени начала!')
                return render(request, 'CreateEvent.html', {'form': form})

            event.save()
            event.save()
            event.Participants.add(request.user)
            return redirect('main page')
    else:
        form = EventForm()
    return render(request, 'CreateEvent.html', {'form': form})