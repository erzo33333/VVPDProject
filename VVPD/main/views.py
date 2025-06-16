from django.http import HttpResponse
from datetime import datetime
from main.models import User, Event
from django.shortcuts import render, redirect, get_object_or_404
from .forms import LoginForm, RegistrationForm, EventForm
from django.contrib import messages
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
from collections import defaultdict

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
    current_user = request.user
    selected_user_id = request.GET.get('user_id')

    # Выбор пользователя
    if selected_user_id:
        try:
            selected_user = current_user.Friends.get(id=selected_user_id)
        except:
            selected_user = current_user
    else:
        selected_user = current_user

    all_users = [current_user] + list(current_user.Friends.all())

    events_qs = Event.objects.filter(Creator=selected_user).order_by('StartTime')
    events_by_day = defaultdict(list)

    placed = defaultdict(list)  # day → list of (start, end, level)

    for e in events_qs:
        start_minutes = e.StartTime.hour * 60 + e.StartTime.minute
        end_minutes = e.EndTime.hour * 60 + e.EndTime.minute
        total_minutes = 24 * 60

        # Смещаем отсчёт от 6:00
        left = ((start_minutes - 360) / total_minutes) * 100
        width = ((end_minutes - start_minutes) / total_minutes) * 100

        if left < 0:
            left = 0
        if width < 0:
            width = 0.5

        date_key = e.StartTime.date()

        # Уровни для перекрывающихся событий
        level = 0
        for placed_event in placed[date_key]:
            if not (end_minutes <= placed_event['start'] or start_minutes >= placed_event['end']):
                if placed_event['level'] == level:
                    level += 1

        placed[date_key].append({'start': start_minutes, 'end': end_minutes, 'level': level})

        events_by_day[date_key].append({
            'Title': e.Title,
            'StartTime': e.StartTime,
            'EndTime': e.EndTime,
            'left': left,
            'width': width,
            'top': level * 50
        })

    return render(request, 'MainPage.html', context={
        'user_list': all_users,
        'selected_user': selected_user,
        'events_by_day': dict(events_by_day)
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


@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if to_user != request.user and request.user not in to_user.FriendshipRequests.all():
        to_user.FriendshipRequests.add(request.user)
    return redirect('user_profile', user_id=to_user.id)


@login_required
def accept_friend_request(request, user_id):
    from_user = get_object_or_404(User, id=user_id)
    if from_user in request.user.FriendshipRequests.all():
        request.user.Friends.add(from_user)
        from_user.Friends.add(request.user)
        request.user.FriendshipRequests.remove(from_user)
    return redirect('friend_requests')


@login_required
def reject_friend_request(request, user_id):
    from_user = get_object_or_404(User, id=user_id)
    if from_user in request.user.FriendshipRequests.all():
        request.user.FriendshipRequests.remove(from_user)
    return redirect('friend_requests')


@login_required
def friend_requests_view(request):
    incoming = request.user.FriendshipRequests.all()
    return render(request, 'friend_requests.html', {'incoming_requests': incoming})