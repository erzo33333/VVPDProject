from django.http import HttpResponse, JsonResponse
from datetime import datetime, date, time, timedelta # MODIFIED: Added time
from main.models import User, Event, UserProfile, Friendship, ChatRoom, Message
from django.shortcuts import render, redirect, get_object_or_404
from .forms import LoginForm, RegistrationForm, UserEditForm, UserProfileForm, EventForm
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
import logging # Import the logging module
from django.contrib import messages # For feedback messages
from django.contrib.auth import get_user_model
from django.core.serializers import serialize
import json
from django.db.models import Q, Count
from django.utils import timezone
import pytz # ADDED

# Get an instance of a logger
logger = logging.getLogger(__name__)


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            logger.info(f"Attempting to authenticate user: {cd['username']}")
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user is not None:
                logger.info(f"User {cd['username']} authenticated successfully.")
                login(request, user)
                return redirect('main_page')
            else:
                logger.warning(f"Authentication failed for user: {cd['username']}")
                return render(request, 'login.html', {'form': form, 'error': 'Неверные учетные данные'})
        else:
            logger.warning(f"Login form is invalid: {form.errors}")
            return render(request, 'login.html', {'form': form, 'error': 'Неверные данные в форме'})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        logger.info(f"Registration form submitted with data: {request.POST}")
        if form.is_valid():
            logger.info("Registration form is valid. Saving user.")
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            logger.info(f"User {new_user.username} created successfully. Redirecting to login.")
            # Optionally, log the user in directly after registration
            # login(request, new_user)
            # return redirect('main page') 
            return redirect('login')
        else:
            # This block will be executed if form.is_valid() is False
            logger.error(f"Registration form is invalid. Errors: {form.errors.as_json()}")
            # It's important to pass the form with errors back to the template
            return render(request, 'register.html', {'form': form, 'error': 'Пожалуйста, исправьте ошибки в форме.'})
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


@login_required(login_url='login')
def main_page(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    user_form = UserEditForm(instance=request.user)
    profile_form = UserProfileForm(instance=user_profile)
    event_form = EventForm()
    
    # TODO: Fetch events for the current user/month to display on the calendar initially
    # events = Event.objects.filter(Creator=request.user) 

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_profile': user_profile,
        'event_form': event_form,
        # 'events': events
    }
    return render(request, 'MainPage.html', context)


@login_required(login_url='login')
def index_page(request):
    return render(request, 'IndexPage.html', context={})


#@login_required(login_url='login')
def second_page(request):
    return render(request, 'SecondPage.html', context={})


@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)
        # For UserProfileForm, we need to handle the case where profile might not exist,
        # though our signal should create it. get_or_create is safer.
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile_form = UserProfileForm(instance=user_profile, data=request.POST, files=request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('main_page') # Corrected name: main_page
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки.')
            # On error, redirecting back to main_page where modal is.
            # Errors are not directly shown in modal unless JS/main_page view handles passing them back.
            return redirect('main_page') # Corrected name: main_page
    else:
        # This handles GET request to /edit_profile/, which shouldn't typically happen with modal form.
        # Redirect to main page regardless.
        return redirect('main_page') # Corrected name: main_page


@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            # Получаем "наивные" datetime из формы
            start_time = form.cleaned_data.get('StartTime')
            end_time = form.cleaned_data.get('EndTime')

            # "Костыль": отнимаем 7 часов
            if start_time:
                start_time -= timedelta(hours=7)
            if end_time:
                end_time -= timedelta(hours=7)

            event = form.save(commit=False)
            # Присваиваем измененные (на 7 часов раньше) "наивные" времена
            event.StartTime = start_time
            event.EndTime = end_time
            
            event.Creator = request.user
            event.save() # Django обработает эти "наивные" времена согласно своим текущим настройкам
            
            return JsonResponse({
                "status": "success",
                "message": "Событие успешно создано!",
                "event": {
                    "id": event.id,
                    "Title": event.Title,
                    "StartTime": event.StartTime.isoformat(), # Будет UTC ISO строка
                    "EndTime": event.EndTime.isoformat(),   # Будет UTC ISO строка
                    "Colour": event.Colour,
                    "Description": event.Description.get('text', '') if isinstance(event.Description, dict) else (event.Description if event.Description is not None else ''),
                    "event_type": event.event_type
                }
            }, status=201)
        else:
            form_errors = {field: [e for e in errors] for field, errors in form.errors.items()}
            return JsonResponse({
                "status": "error",
                "message": "Пожалуйста, исправьте ошибки в форме.",
                "errors": form_errors
            }, status=400)
    else: 
        return JsonResponse({"status": "error", "message": "Invalid request method. POST required."}, status=405)


@login_required
def get_month_events(request, year, month):
    # Ensure user can only fetch their own events for now
    # Later, this can be expanded for viewing friends' calendars with privacy checks
    events = Event.objects.filter(
        Creator=request.user, # Consider also showing events where user is a Participant
        StartTime__year=year,
        StartTime__month=month
    ).distinct() 
    
    event_list = []
    for event in events:
        event_list.append({
            'id': event.id,
            'title': event.Title,
            'start': event.StartTime.isoformat(), 
            'end': event.EndTime.isoformat(),
            'description': event.Description, # This will be the dict, e.g., {"text": "..."}
            'event_type': event.event_type,
            'color': event.Colour, 
        })
    return JsonResponse(event_list, safe=False)


@login_required
def get_event_details(request, event_id):
    event = get_object_or_404(Event, id=event_id, Creator=request.user) # Ensure user owns event
    # Or check if user is a participant if they should be able to view/edit events they are invited to
    data = {
        'id': event.id,
        'Title': event.Title,
        'StartTime': event.StartTime.isoformat(),
        'EndTime': event.EndTime.isoformat(),
        'Description': event.Description.get('text', '') if isinstance(event.Description, dict) else event.Description, # Extract text
        'event_type': event.event_type,
        'Colour': event.Colour,
        # Add participants later if needed for edit form
    }
    return JsonResponse(data)


@login_required
def get_day_events(request, year, month, day):
    target_date = datetime.date(year, month, day)
    logger.info(f"[get_day_events] Requested for date: {target_date}")
    # Fetch events that are active on the target_date
    # An event is active if its StartTime (date part) <= target_date AND EndTime (date part) >= target_date
    events_qs = Event.objects.filter(
        Q(Creator=request.user), # Or Q(Participants=request.user) if they should see events they are part of
        Q(StartTime__date__lte=target_date),
        Q(EndTime__date__gte=target_date)
    ).distinct().order_by('StartTime')

    logger.info(f"[get_day_events] Found {events_qs.count()} events for {target_date} before serialization.")
    for ev in events_qs:
        logger.info(f"  - Event ID: {ev.id}, Title: {ev.Title}, Start: {ev.StartTime}, End: {ev.EndTime}")

    event_list = []
    for event in events_qs:
        event_list.append({
            'id': event.id,
            'title': event.Title,
            'start': event.StartTime.isoformat(),
            'end': event.EndTime.isoformat(),
            'description_text': event.Description.get('text', '') if isinstance(event.Description, dict) else event.Description,
            'event_type': event.event_type,
            'color': event.Colour,
        })
    return JsonResponse(event_list, safe=False)


@login_required
def edit_event(request, event_id):
    try:
        event_instance = Event.objects.get(id=event_id, Creator=request.user)
    except Event.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Событие не найдено или у вас нет прав на его редактирование."}, status=404)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event_instance)
        if form.is_valid():
            # Получаем "наивные" datetime из формы
            start_time = form.cleaned_data.get('StartTime')
            end_time = form.cleaned_data.get('EndTime')

            # "Костыль": отнимаем 7 часов
            if start_time:
                start_time -= timedelta(hours=7)
            if end_time:
                end_time -= timedelta(hours=7)

            event = form.save(commit=False)
            # Присваиваем измененные (на 7 часов раньше) "наивные" времена
            event.StartTime = start_time
            event.EndTime = end_time
            
            event.save() # Django обработает эти "наивные" времена согласно своим текущим настройкам
            
            return JsonResponse({
                "status": "success",
                "message": "Событие успешно обновлено!",
                "event": {
                    "id": event.id,
                    "Title": event.Title,
                    "StartTime": event.StartTime.isoformat(), # Будет UTC ISO строка
                    "EndTime": event.EndTime.isoformat(),   # Будет UTC ISO строка
                    "Colour": event.Colour,
                    "Description": event.Description.get('text', '') if isinstance(event.Description, dict) else (event.Description if event.Description is not None else ''),
                    "event_type": event.event_type
                }
            }, status=200)
        else:
            form_errors = {field: [e for e in errors] for field, errors in form.errors.items()}
            return JsonResponse({
                "status": "error",
                "message": "Пожалуйста, исправьте ошибки в форме.",
                "errors": form_errors
            }, status=400)
    else: 
        return JsonResponse({"status": "error", "message": "Invalid request method. POST required for update."}, status=405)


@login_required
def delete_event(request, event_id):
    if request.method == 'POST':
        try:
            event = Event.objects.get(id=event_id, Creator=request.user)
            event.delete()
            return JsonResponse({"status": "success", "message": "Событие успешно удалено."}, status=200)
        except Event.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Событие не найдено или у вас нет прав на его удаление."}, status=404)
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return JsonResponse({"status": "error", "message": "Произошла ошибка при удалении события."}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request method. POST required."}, status=405)


@login_required
def user_list(request):
    users = User.objects.exclude(id=request.user.id) # Exclude self
    # Further filtering: exclude users already friends or with pending requests?
    # For now, let's keep it simple.
    return render(request, 'main/user_list.html', {'users': users})


@login_required
def send_friend_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    if request.user == receiver:
        messages.error(request, "Вы не можете добавить себя в друзья.")
        return redirect('user_list')

    # Check if a request already exists or they are already friends
    if Friendship.objects.filter(
        (Q(requester=request.user, receiver=receiver)) |
        (Q(requester=receiver, receiver=request.user))
    ).exists():
        messages.info(request, f"Запрос пользователю {receiver.username} уже отправлен или вы уже друзья.")
        return redirect('user_list')

    Friendship.objects.create(requester=request.user, receiver=receiver)
    messages.success(request, f"Запрос в друзья отправлен пользователю {receiver.username}.")
    return redirect('user_list')


@login_required
def friend_requests(request):
    incoming_requests = Friendship.objects.filter(receiver=request.user, status='pending')
    return render(request, 'main/friend_requests.html', {'requests': incoming_requests})


@login_required
def accept_friend_request(request, request_id):
    friend_request = get_object_or_404(Friendship, id=request_id, receiver=request.user, status='pending')
    friend_request.status = 'accepted'
    friend_request.save()
    messages.success(request, f"Запрос от {friend_request.requester.username} принят.")
    return redirect('friend_requests')


@login_required
def decline_friend_request(request, request_id):
    friend_request = get_object_or_404(Friendship, id=request_id, receiver=request.user, status='pending')
    # Option 1: Change status to 'declined'
    friend_request.status = 'declined'
    friend_request.save()
    # Option 2: Delete the request entirely
    # friend_request.delete()
    messages.info(request, f"Запрос от {friend_request.requester.username} отклонен.")
    return redirect('friend_requests')


@login_required
def friend_list(request):
    # Friends are where status is 'accepted' and request.user is either requester or receiver
    friends = User.objects.filter(
        Q(friendship_requests_sent__receiver=request.user, friendship_requests_sent__status='accepted') |
        Q(friendship_requests_received__requester=request.user, friendship_requests_received__status='accepted')
    ).distinct()
    return render(request, 'main/friend_list.html', {'friends': friends})


@login_required
def remove_friend(request, user_id):
    friend_to_remove = get_object_or_404(User, id=user_id)
    # Find and delete the friendship record(s)
    friendship = Friendship.objects.filter(
        (Q(requester=request.user, receiver=friend_to_remove) | Q(requester=friend_to_remove, receiver=request.user)),
        status='accepted'
    )
    if friendship.exists():
        friendship.delete()
        messages.success(request, f"Пользователь {friend_to_remove.username} удален из друзей.")
    else:
        messages.error(request, "Этот пользователь не является вашим другом или произошла ошибка.")
    return redirect('friend_list')


@login_required
def chat_room_list(request):
    # Get chat rooms where the current user is a participant
    chat_rooms = ChatRoom.objects.filter(participants=request.user).order_by('-last_message_at')
    return render(request, 'main/chat_room_list.html', {'chat_rooms': chat_rooms})


@login_required
def chat_room_detail(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    messages_list = Message.objects.filter(chat_room=chat_room).order_by('timestamp')
    # Determine the other participant(s) for display purposes
    other_participants = chat_room.participants.exclude(id=request.user.id)
    chat_name = chat_room.name or ", ".join([user.username for user in other_participants])
    return render(request, 'main/chat_room_detail.html', {
        'chat_room': chat_room,
        'messages_list': messages_list,
        'chat_name': chat_name,
        'other_participants': other_participants
    })


@login_required
def start_or_get_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        messages.error(request, "Вы не можете начать чат с самим собой.")
        return redirect('friend_list') # Or user_list, or wherever appropriate

    # Try to find an existing 1-on-1 chat room
    # This logic assumes 1-on-1 chats don't have a pre-set name and involve exactly two users.
    # For group chats, this logic would need to be different.
    chat_room = ChatRoom.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).annotate(
        num_participants=models.Count('participants')
    ).filter(num_participants=2).first()

    if not chat_room:
        # Create a new 1-on-1 chat room if one doesn't exist
        chat_room = ChatRoom.objects.create()
        chat_room.participants.add(request.user, other_user)
        # No specific name for 1-on-1 chats by default
    
    return redirect('chat_room_detail', room_id=chat_room.id)


@login_required
def send_message(request, room_id):
    chat_room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(chat_room=chat_room, sender=request.user, content=content)
            chat_room.last_message_at = timezone.now() # Update last message time for sorting
            chat_room.save()
            # For AJAX, return JsonResponse. For forms, redirect.
            return redirect('chat_room_detail', room_id=room_id)
        else:
            messages.error(request, "Сообщение не может быть пустым.")
    return redirect('chat_room_detail', room_id=room_id) # Or render with error


@login_required
def friend_list_api(request):
    user_friends = []
    # Друзья, где текущий пользователь является отправителем запроса
    friendships_sent = Friendship.objects.filter(requester=request.user, status='accepted').select_related('receiver__profile', 'receiver')
    for friendship in friendships_sent:
        profile_picture_url = None
        if hasattr(friendship.receiver, 'profile') and friendship.receiver.profile and friendship.receiver.profile.profile_picture:
            profile_picture_url = friendship.receiver.profile.profile_picture.url
        user_friends.append({
            "id": friendship.receiver.id,
            "username": friendship.receiver.username,
            "profile_picture_url": profile_picture_url
        })
    
    # Друзья, где текущий пользователь является получателем запроса
    friendships_received = Friendship.objects.filter(receiver=request.user, status='accepted').select_related('requester__profile', 'requester')
    for friendship in friendships_received:
        profile_picture_url = None
        if hasattr(friendship.requester, 'profile') and friendship.requester.profile and friendship.requester.profile.profile_picture:
            profile_picture_url = friendship.requester.profile.profile_picture.url
        # Избегаем дублирования, если дружба как-то оказалась в обе стороны
        if not any(f['id'] == friendship.requester.id for f in user_friends):
            user_friends.append({
                "id": friendship.requester.id,
                "username": friendship.requester.username,
                "profile_picture_url": profile_picture_url
            })
            
    return JsonResponse(user_friends, safe=False)


@login_required
def chat_room_list_api(request):
    # Placeholder: Fetch chat rooms for the current user
    # You need to implement the logic to retrieve chat rooms, their last messages, participants etc.
    chat_rooms_data = []
    chat_rooms = ChatRoom.objects.filter(participants=request.user).prefetch_related('participants__profile').order_by('-last_message_at')
    
    for room in chat_rooms:
        last_msg_obj = Message.objects.filter(room=room).order_by('-timestamp').first()
        participants_data = []
        other_participant = None # For 1-on-1 chats
        
        for participant in room.participants.all():
            if participant != request.user:
                other_participant = participant # Capture the other participant
                participants_data.append({
                    "id": participant.id,
                    "username": participant.username,
                    "profile_picture_url": participant.profile.profile_picture.url if hasattr(participant, 'profile') and participant.profile.profile_picture else None
                })
        
        room_name = room.name
        if not room_name and other_participant: # If it's a 1-on-1 chat without a group name
            room_name = other_participant.username

        chat_rooms_data.append({
            "id": room.id,
            "name": room_name, # For 1-on-1, JS will use other participant's name if this is null/empty
            "last_message": last_msg_obj.content if last_msg_obj else "Нет сообщений",
            "last_message_at_display": last_msg_obj.timestamp.strftime("%H:%M") if last_msg_obj else "", # Format as needed
            "participants": participants_data # JS expects this to determine 1-on-1 or group, and get other user info
        })

    return JsonResponse(chat_rooms_data, safe=False)


@login_required
def friend_requests_count_api(request):
    count = Friendship.objects.filter(receiver=request.user, status='pending').count()
    return JsonResponse({"count": count})


@login_required
def api_events_for_day(request, date_str): # date_str is YYYY-MM-DD in KRT
    logger.info(f"[api_events_for_day] Received KRT date_str: {date_str}")
    try:
        # 1. Define Krasnoyarsk timezone
        krt_tz = pytz.timezone('Asia/Krasnoyarsk')

        # 2. Parse date_str (YYYY-MM-DD) into a datetime.date object
        # 'datetime' here refers to the datetime.datetime class from the import
        parsed_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        # 3. Create a naive datetime.datetime object representing 6 AM on the parsed_date_obj
        # This is 6 AM in Krasnoyarsk time for the given calendar day.
        # 'datetime.combine' uses the datetime.datetime class method.
        # 'time(6,0,0)' uses the imported 'time' class constructor.
        view_window_start_naive_krt = datetime.combine(parsed_date_obj, time(6, 0, 0))

        # 4. Localize this naive KRT datetime to make it timezone-aware
        view_window_start_aware_krt = krt_tz.localize(view_window_start_naive_krt)

        # 5. Convert this KRT datetime to UTC for database queries
        view_window_start_utc = view_window_start_aware_krt.astimezone(pytz.utc)

        # 6. Calculate the end of the 24-hour window in UTC
        # (6 AM KRT on date_str to 6 AM KRT on the next day)
        view_window_end_utc = view_window_start_utc + timedelta(days=1)

        logger.info(f"[api_events_for_day] Query window UTC: {view_window_start_utc.isoformat()} to {view_window_end_utc.isoformat()}")

        # 7. Fetch events that overlap with this [view_window_start_utc, view_window_end_utc) interval
        events_qs = Event.objects.filter(
            Q(Creator=request.user), # Consider other participant logic if needed
            Q(StartTime__lt=view_window_end_utc),    # Event starts before the window ends
            Q(EndTime__gt=view_window_start_utc)     # Event ends after the window starts
        ).distinct().order_by('StartTime')

        logger.info(f"[api_events_for_day] Found {events_qs.count()} events for KRT date {date_str} (UTC window: {view_window_start_utc} - {view_window_end_utc})")

        event_list = []
        for event in events_qs:
            event_list.append({
                'id': event.id,
                'Title': event.Title,
                'StartTime': event.StartTime.isoformat(), # Still send as ISO UTC
                'EndTime': event.EndTime.isoformat(),     # Still send as ISO UTC
                'Description': event.Description.get('text', '') if isinstance(event.Description, dict) else (event.Description if event.Description is not None else ''),
                'event_type': event.event_type,
                'Colour': event.Colour,
            })
        return JsonResponse(event_list, safe=False)

    except ValueError as e:
        logger.error(f"[api_events_for_day] Invalid date format for date_str='{date_str}': {e}")
        return JsonResponse({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}, status=400)
    except Exception as e:
        logger.error(f"[api_events_for_day] Error processing request for date_str='{date_str}': {e}")
        # It's good to log the full traceback for unexpected errors
        logger.exception(f"Full traceback for error in api_events_for_day with date_str='{date_str}':")
        return JsonResponse({"status": "error", "message": "An error occurred while fetching events."}, status=500)


@login_required
def api_event_detail(request, event_id):
    try:
        event = Event.objects.get(id=event_id, Creator=request.user)
        event_data = {
            "id": event.id,
            "Title": event.Title,
            "StartTime": event.StartTime.isoformat(),
            "EndTime": event.EndTime.isoformat(),
            "Colour": event.Colour,
            "Description": event.Description.get('text', '') if isinstance(event.Description, dict) else (event.Description if event.Description is not None else ''),
            "event_type": event.event_type
            # Add other fields if needed by the form
        }
        return JsonResponse(event_data)
    except Event.DoesNotExist:
        return JsonResponse({"error": "Event not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)