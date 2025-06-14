from django.http import HttpResponse
from datetime import datetime
from main.models import User, Event
from django.shortcuts import render, redirect, get_object_or_404
from .forms import LoginForm, RegistrationForm
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
    schedules = {
        u.id: Event.objects.filter(Participants=u).order_by('StartTime')
        for u in all_users
    }
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


@login_required(login_url='login')
def user_schedule_view(request, username):
    viewed_user = get_object_or_404(User, username=username)
    events = Event.objects.filter(Creator=viewed_user).order_by('StartTime')
    is_own_schedule = viewed_user == request.user
    friends = request.user.Friends.all()
    return render(request, 'UserSchedule.html', context={
        'viewed_user': viewed_user,
        'events': events,
        'is_own_schedule': viewed_user == request.user
    })