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
from django.db import transaction # ADDED FOR FRIENDSHIP MANAGEMENT

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
    users = User.objects.all()
    return render(request, 'user_list.html', {'users': users})


@login_required
@transaction.atomic
def send_friend_request(request, to_user_id):
    if request.method == 'POST':
        to_user = get_object_or_404(User, id=to_user_id)
        from_user = request.user

        if to_user == from_user:
            return JsonResponse({'status': 'error', 'message': 'Вы не можете отправить запрос дружбы самому себе.'}, status=400)

        # Проверка, не являются ли они уже друзьями
        if from_user.profile.friends.filter(id=to_user.id).exists():
            return JsonResponse({'status': 'error', 'message': 'Этот пользователь уже ваш друг.'}, status=400)

        # Проверка на существующий запрос (в любую сторону)
        existing_request = Friendship.objects.filter(
            (Q(requester=from_user, receiver=to_user) | Q(requester=to_user, receiver=from_user))
        ).first()

        if existing_request:
            if existing_request.status == 'pending':
                if existing_request.requester == from_user:
                    return JsonResponse({'status': 'info', 'message': 'Запрос дружбы уже отправлен этому пользователю.'}, status=200)
                else: # existing_request.receiver == from_user
                    return JsonResponse({'status': 'info', 'message': 'Этот пользователь уже отправил вам запрос. Проверьте свои заявки.'}, status=200)
            elif existing_request.status == 'accepted': # Должно быть отловлено проверкой friends выше, но на всякий случай
                return JsonResponse({'status': 'error', 'message': 'Этот пользователь уже ваш друг.'}, status=400)
            elif existing_request.status == 'declined':
                # Если ранее был отклонен, можно отправить новый (или переоткрыть старый)
                existing_request.requester = from_user # На случай, если роли поменялись
                existing_request.receiver = to_user
                existing_request.status = 'pending'
                existing_request.save()
                return JsonResponse({'status': 'success', 'message': 'Запрос дружбы повторно отправлен.'}, status=200)
        
        Friendship.objects.create(requester=from_user, receiver=to_user, status='pending')
        return JsonResponse({'status': 'success', 'message': 'Запрос дружбы отправлен.'}, status=201)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
def api_get_pending_friend_requests(request):
    friend_requests = Friendship.objects.filter(receiver=request.user, status='pending').select_related('requester__profile')
    requests_data = []
    for fr in friend_requests:
        profile_pic_url = None
        if fr.requester.profile.profile_picture:
            profile_pic_url = fr.requester.profile.profile_picture.url
        requests_data.append({
            'id': fr.id,
            'requester_id': fr.requester.id,
            'requester_username': fr.requester.username,
            'requester_profile_pic': profile_pic_url,
            'created_at': fr.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return JsonResponse(requests_data, safe=False)


@login_required
@transaction.atomic
def accept_friend_request(request, friendship_id):
    if request.method == 'POST':
        friend_request = get_object_or_404(Friendship, id=friendship_id)
        
        if friend_request.receiver != request.user:
            return JsonResponse({'status': 'error', 'message': 'У вас нет прав принять этот запрос.'}, status=403)
        
        if friend_request.status != 'pending':
             return JsonResponse({'status': 'error', 'message': 'Этот запрос уже был обработан.'}, status=400)

        friend_request.status = 'accepted'
        friend_request.save()

        # Добавляем в друзья в обе стороны
        request.user.profile.friends.add(friend_request.requester)
        friend_request.requester.profile.friends.add(request.user)
        
        # Если был встречный запрос, его тоже можно принять или удалить
        counter_request = Friendship.objects.filter(
            requester=friend_request.receiver, 
            receiver=friend_request.requester, 
            status='pending'
        ).first()
        if counter_request:
            counter_request.status = 'accepted' # или удалить, если логика этого требует
            counter_request.save()

        return JsonResponse({'status': 'success', 'message': 'Запрос дружбы принят.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
@transaction.atomic
def reject_friend_request(request, friendship_id): # Renamed from decline_friend_request for consistency
    if request.method == 'POST':
        friend_request = get_object_or_404(Friendship, id=friendship_id)
        
        if friend_request.receiver != request.user:
            return JsonResponse({'status': 'error', 'message': 'У вас нет прав отклонить этот запрос.'}, status=403)

        if friend_request.status != 'pending':
             return JsonResponse({'status': 'error', 'message': 'Этот запрос уже был обработан.'}, status=400)

        friend_request.status = 'declined'
        friend_request.save()
        return JsonResponse({'status': 'success', 'message': 'Запрос дружбы отклонен.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


@login_required
def api_get_friends(request): # Replaces friend_list
    friends = request.user.profile.friends.all().select_related('profile')
    friends_data = []
    for friend in friends: # friend is a User object
        profile_pic_url = None
        # Ensure friend.profile exists and friend.profile.profile_picture is not None before accessing .url
        if hasattr(friend, 'profile') and friend.profile and friend.profile.profile_picture:
            profile_pic_url = friend.profile.profile_picture.url
            
        # Пытаемся найти последний чат с этим другом (1-на-1)
        # Это может быть неэффективно если много друзей, лучше вынести в отдельный запрос при необходимости
        chat_room = ChatRoom.objects.annotate(
            num_participants=Count('participants')
        ).filter(
            num_participants=2, 
            participants=request.user
        ).filter(
            participants=friend
        ).first()

        friends_data.append({
            'id': friend.id,
            'username': friend.username,
            'profile_picture_url': profile_pic_url,
            'chat_room_id': chat_room.id if chat_room else None 
        })
    return JsonResponse(friends_data, safe=False)


@login_required
@transaction.atomic
def remove_friend(request, friend_user_id):
    if request.method == 'POST':
        friend_user = get_object_or_404(User, id=friend_user_id)
        current_user = request.user

        if not current_user.profile.friends.filter(id=friend_user.id).exists():
            return JsonResponse({'status': 'error', 'message': 'Этот пользователь не является вашим другом.'}, status=400)

        # Удаляем из списков друзей друг у друга
        current_user.profile.friends.remove(friend_user)
        friend_user.profile.friends.remove(current_user)

        # Находим и удаляем или помечаем записи Friendship
        Friendship.objects.filter(
            (Q(requester=current_user, receiver=friend_user) | Q(requester=friend_user, receiver=current_user)) &
            Q(status='accepted')
        ).delete() # Или обновить статус, если хотим хранить историю

        return JsonResponse({'status': 'success', 'message': f'Пользователь {friend_user.username} удален из ваших друзей.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def api_search_users(request):
    query = request.GET.get('q', '')
    if not query or len(query) < 2: # Минимум 2 символа для поиска
        return JsonResponse({'users': [], 'message': 'Введите минимум 2 символа для поиска.'}, status=200)

    current_user = request.user
    # Исключаем себя, своих текущих друзей
    # Дополнительно, можно исключить тех, кому уже отправлен запрос или от кого получен
    
    users_qs = User.objects.filter(
        Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
    ).exclude(id=current_user.id).select_related('profile')

    users_data = []
    for user in users_qs:
        status = 'can_send_request'
        profile_pic_url = None # Initialize
        # Ensure user.profile exists and user.profile.profile_picture is not None before accessing .url
        if hasattr(user, 'profile') and user.profile and user.profile.profile_picture:
            profile_pic_url = user.profile.profile_picture.url

        if current_user.profile.friends.filter(id=user.id).exists():
            status = 'already_friends'
        else:
            # Проверка исходящего запроса
            if Friendship.objects.filter(requester=current_user, receiver=user, status='pending').exists():
                status = 'request_sent'
            # Проверка входящего запроса
            elif Friendship.objects.filter(requester=user, receiver=current_user, status='pending').exists():
                status = 'request_received'
        
        users_data.append({
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'profile_picture_url': profile_pic_url,
            'status': status # can_send_request, already_friends, request_sent, request_received
        })
        
    return JsonResponse({'users': users_data})


@login_required
@transaction.atomic
def api_create_group_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            group_name = data.get('name')
            participant_ids = data.get('participant_ids') # Expecting a list of user IDs

            if not group_name or not group_name.strip():
                return JsonResponse({'status': 'error', 'message': 'Название группы не может быть пустым.'}, status=400)
            
            if not participant_ids or not isinstance(participant_ids, list) or len(participant_ids) == 0:
                return JsonResponse({'status': 'error', 'message': 'Выберите хотя бы одного участника для группы.'}, status=400)

            # Ensure all participant IDs are valid users and distinct
            # Also ensure that participant_ids does not contain the request.user.id, as creator is added separately
            actual_participant_ids = [pid for pid in set(participant_ids) if pid != request.user.id]
            
            if not actual_participant_ids: # if after removing self, no one is left
                 if request.user.id in participant_ids and len(set(participant_ids)) == 1:
                     # This case is fine if it's a group of one, but usually groups have >1.
                     # For now, let's assume a group needs at least one OTHER member.
                     # If a group of one is desired, this logic might need adjustment.
                     # OR, if participant_ids was *only* the creator, it means they didn't select anyone else.
                     pass # Allow creating a group where only creator is a participant initially.

            # Fetch user objects for the given IDs, excluding the creator if already in the list.
            participants_to_add = User.objects.filter(id__in=actual_participant_ids)
            
            # Validate if all provided distinct non-creator IDs correspond to actual users
            if len(participants_to_add) != len(actual_participant_ids):
                 return JsonResponse({'status': 'error', 'message': 'Один или несколько выбранных пользователей не существуют.'}, status=400)

            # Create the group chat
            chat_room = ChatRoom.objects.create(
                name=group_name,
                creator=request.user,
                is_group=True
            )
            
            # Add participants
            chat_room.participants.add(request.user) # Creator is always a participant
            if actual_participant_ids: # Add other selected users
                chat_room.participants.add(*participants_to_add) 
            
            chat_room.last_message_at = timezone.now() # Initialize for sorting
            chat_room.save()

            return JsonResponse({
                'status': 'success',
                'message': f'Группа "{group_name}" успешно создана.',
                'room_id': chat_room.id,
                'room_name': chat_room.name,
                'is_group': chat_room.is_group,
                'creator_id': request.user.id,
                'participant_ids': [request.user.id] + list(actual_participant_ids) # All participants
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Неверный формат JSON.'}, status=400)
        # User.DoesNotExist might occur if an ID in participant_ids is invalid, though filter should catch it.
        # However, direct .get() is no longer used for participant list construction.
        except Exception as e:
            logger.error(f"Error creating group chat: {e}")
            return JsonResponse({'status': 'error', 'message': 'Произошла ошибка при создании группы.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Метод не разрешен. Требуется POST.'}, status=405)


@login_required
@transaction.atomic # Ensure atomicity for chat creation and adding participants
def api_get_or_create_private_chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    current_user = request.user

    if other_user == current_user:
        return JsonResponse({'status': 'error', 'message': 'Вы не можете начать чат с самим собой.'}, status=400)

    # Try to find an existing 1-on-1 chat room
    # A 1-on-1 chat is identified by having exactly two participants: current_user and other_user, and no explicit name.
    chat_room = ChatRoom.objects.annotate(
        num_participants=Count('participants')
    ).filter(
        participants=current_user
    ).filter(
        participants=other_user
    ).filter(
        num_participants=2
    ).filter(
        name__isnull=True  # Explicitly for 1-on-1 chats that don't have a group name
    ).first()

    if not chat_room:
        # Create a new 1-on-1 chat room if one doesn\'t exist
        chat_room = ChatRoom.objects.create()
        chat_room.participants.add(current_user, other_user)
        chat_room.last_message_at = timezone.now() # Initialize for sorting
        chat_room.save()
        logger.info(f"Created new private chat room between {current_user.username} and {other_user.username}, ID: {chat_room.id}")
    else:
        logger.info(f"Found existing private chat room between {current_user.username} and {other_user.username}, ID: {chat_room.id}")

    return JsonResponse({'status': 'success', 'room_id': chat_room.id})


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
    chat_rooms_data = []
    # Eager load related participants and their profiles to reduce DB queries in loop
    chat_rooms = ChatRoom.objects.filter(participants=request.user).prefetch_related('participants__profile', 'creator').order_by('-last_message_at')
    
    for room in chat_rooms:
        last_msg_obj = Message.objects.filter(chat_room=room).order_by('-timestamp').first() # Corrected: chat_room=room
        
        all_participants_info = []
        all_participant_ids = []
        other_participant_for_name = None # For 1-on-1 chat name

        for p in room.participants.all():
            all_participant_ids.append(p.id)
            profile_pic_url = None
            if hasattr(p, 'profile') and p.profile and p.profile.profile_picture:
                profile_pic_url = p.profile.profile_picture.url
            
            all_participants_info.append({
                "id": p.id,
                "username": p.username,
                "profile_picture_url": profile_pic_url
            })
            if p != request.user and not room.is_group:
                other_participant_for_name = p

        display_name = room.name # Use group name if available
        if not display_name and room.is_group: # Should not happen if group name is mandatory
             display_name = f"Группа {room.id}"
        elif not room.is_group and other_participant_for_name:
            display_name = other_participant_for_name.username
        elif not room.is_group: # 1-on-1 chat, but other participant somehow not found (e.g. self-chat, or data issue)
            # This case should ideally not happen in a clean 1-on-1 setup.
            # Fallback name, or perhaps filter out such rooms earlier if they are invalid.
            participant_usernames = [p_info['username'] for p_info in all_participants_info if p_info['id'] != request.user.id]
            if participant_usernames:
                display_name = ", ".join(participant_usernames)
            else: # Only self in a 1-on-1? Unlikely.
                display_name = f"Чат {room.id}"


        chat_rooms_data.append({
            "id": room.id,
            "name": display_name, 
            "is_group": room.is_group,
            "creator_id": room.creator.id if room.creator else None,
            "all_participant_ids": all_participant_ids, # List of all participant IDs
            "participants_details": all_participants_info, # More detailed info if needed by UI directly in chat list
            "last_message_content": last_msg_obj.content if last_msg_obj else "Нет сообщений",
            "last_message_timestamp": last_msg_obj.timestamp.isoformat() if last_msg_obj else None,
            "last_message_at_display": last_msg_obj.timestamp.strftime("%H:%M") if last_msg_obj else "",
        })

    return JsonResponse(chat_rooms_data, safe=False)


@login_required
def friend_requests_count_api(request):
    count = Friendship.objects.filter(receiver=request.user, status='pending').count()
    return JsonResponse({"count": count})


@login_required
def api_events_for_day(request, user_id, date_str): # date_str is YYYY-MM-DD in KRT, user_id is the ID of the schedule owner
    logger.info(f"[api_events_for_day] Requested for user_id: {user_id}, KRT date_str: {date_str}")
    
    try:
        target_user = get_object_or_404(User, id=user_id)
        target_user_profile = get_object_or_404(UserProfile, user=target_user)

        can_view_schedule = False
        if target_user == request.user: # User is requesting their own schedule
            can_view_schedule = True
        else:
            # Check privacy settings of the target_user
            privacy = target_user_profile.privacy_schedule_visibility
            if privacy == 'all':
                can_view_schedule = True
            elif privacy == 'friends':
                # Check if request.user is friends with target_user
                is_friend = Friendship.objects.filter(
                    (Q(requester=request.user, receiver=target_user) | Q(requester=target_user, receiver=request.user)),
                    status='accepted'
                ).exists()
                if is_friend:
                    can_view_schedule = True
            # If privacy is 'only_me', can_view_schedule remains False unless target_user is request.user

        if not can_view_schedule:
            logger.warn(f"[api_events_for_day] Access denied for user {request.user.id} to view schedule of user {target_user.id}")
            return JsonResponse({"status": "error", "message": "Доступ к расписанию этого пользователя ограничен."}, status=403)

        # Proceed to fetch events if can_view_schedule is True
        krt_tz = pytz.timezone('Asia/Krasnoyarsk')
        parsed_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        view_window_start_naive_krt = datetime.combine(parsed_date_obj, time(6, 0, 0))
        view_window_start_aware_krt = krt_tz.localize(view_window_start_naive_krt)
        view_window_start_utc = view_window_start_aware_krt.astimezone(pytz.utc)
        view_window_end_utc = view_window_start_utc + timedelta(days=1)

        logger.info(f"[api_events_for_day] Querying events for user {target_user.id} in UTC window: {view_window_start_utc.isoformat()} to {view_window_end_utc.isoformat()}")

        events_qs = Event.objects.filter(
            Q(Creator=target_user), # Fetch events for the target_user
            Q(StartTime__lt=view_window_end_utc),
            Q(EndTime__gt=view_window_start_utc)
        ).distinct().order_by('StartTime')

        event_list = []
        for event in events_qs:
            event_list.append({
                'id': event.id,
                'Title': event.Title,
                'StartTime': event.StartTime.isoformat(),
                'EndTime': event.EndTime.isoformat(),
                'Description': event.Description.get('text', '') if isinstance(event.Description, dict) else (event.Description if event.Description is not None else ''),
                'event_type': event.event_type,
                'Colour': event.Colour,
            })
        return JsonResponse(event_list, safe=False)

    except User.DoesNotExist:
        logger.error(f"[api_events_for_day] Target user with id {user_id} not found.")
        return JsonResponse({"status": "error", "message": "Пользователь не найден."}, status=404)
    except UserProfile.DoesNotExist:
        logger.error(f"[api_events_for_day] UserProfile for user id {user_id} not found.")
        # This case might indicate data inconsistency, but for the client, it's similar to user not found or access issue.
        return JsonResponse({"status": "error", "message": "Профиль пользователя не найден."}, status=404)
    except ValueError as e:
        logger.error(f"[api_events_for_day] Invalid date format for date_str='{date_str}': {e}")
        return JsonResponse({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}, status=400)
    except Exception as e:
        logger.exception(f"[api_events_for_day] Error processing request for user_id={user_id}, date_str='{date_str}':")
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

@login_required
def api_get_chat_messages(request, room_id):
    try:
        chat_room = get_object_or_404(ChatRoom, id=room_id)
        # Check if the requesting user is a participant of the chat room
        if request.user not in chat_room.participants.all():
            return JsonResponse({"status": "error", "message": "Access denied."}, status=403)

        messages_qs = Message.objects.filter(chat_room=chat_room).order_by('timestamp').select_related('sender', 'sender__profile')
        
        messages_data = []
        for msg in messages_qs:
            profile_picture_url = None
            if hasattr(msg.sender, 'profile') and msg.sender.profile and msg.sender.profile.profile_picture:
                profile_picture_url = msg.sender.profile.profile_picture.url

            messages_data.append({
                "id": msg.id,
                "sender_id": msg.sender.id,
                "sender_username": msg.sender.username,
                "sender_profile_picture_url": profile_picture_url,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(), # Send as ISO string
                # Consider formatting timestamp for display on client-side if needed e.g. msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return JsonResponse(messages_data, safe=False)

    except ChatRoom.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Chat room not found."}, status=404)
    except Exception as e:
        logger.exception(f"[api_get_chat_messages] Error fetching messages for room_id={room_id}:")
        return JsonResponse({"status": "error", "message": "An error occurred while fetching messages."}, status=500)


@login_required
@transaction.atomic
def api_leave_group_chat(request, room_id):
    if request.method == 'POST': # Or can be DELETE method
        try:
            chat_room = get_object_or_404(ChatRoom, id=room_id, is_group=True)
            user = request.user

            if user not in chat_room.participants.all():
                return JsonResponse({'status': 'error', 'message': 'Вы не являетесь участником этого чата.'}, status=403)

            chat_room.participants.remove(user)
            
            # Optional: if the user was the creator, nullify the creator field or reassign
            if chat_room.creator == user:
                # Option 1: Set creator to None if no other logic for creator re-assignment
                # chat_room.creator = None 
                # Option 2: Or, if desired, assign a new creator (e.g., the oldest remaining participant)
                # This can be complex; for now, we might just leave it or set to None.
                # If creator must exist, and was the last person, this needs more thought.
                pass # For now, do nothing specific if creator leaves. Consider implications.

            # Optional: Delete chat room if no participants are left
            if chat_room.participants.count() == 0:
                chat_room.delete()
                return JsonResponse({'status': 'success', 'message': 'Вы покинули группу, и она была удалена, так как в ней не осталось участников.'})
            else:
                # Update last_message_at to ensure the chat order might reflect this change if needed
                # Or, add a system message to the chat about the user leaving.
                chat_room.last_message_at = timezone.now()
                chat_room.save()
                return JsonResponse({'status': 'success', 'message': 'Вы успешно покинули группу.'})

        except ChatRoom.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Групповой чат не найден.'}, status=404)
        except Exception as e:
            logger.error(f"Error leaving group chat (room_id={room_id}, user_id={request.user.id}): {e}")
            return JsonResponse({'status': 'error', 'message': 'Произошла ошибка при выходе из группы.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Метод не разрешен. Требуется POST (или DELETE).'}, status=405)


@login_required
@transaction.atomic
def api_add_participants_to_group_chat(request, room_id):
    if request.method == 'POST':
        try:
            chat_room = get_object_or_404(ChatRoom, id=room_id, is_group=True)
            user = request.user

            if user not in chat_room.participants.all():
                return JsonResponse({'status': 'error', 'message': 'Вы должны быть участником группы, чтобы добавлять новых пользователей.'}, status=403)

            data = json.loads(request.body)
            new_participant_ids = data.get('participant_ids')

            if not new_participant_ids or not isinstance(new_participant_ids, list):
                return JsonResponse({'status': 'error', 'message': 'Список ID участников не предоставлен или имеет неверный формат.'}, status=400)

            added_users_count = 0
            errors = []
            current_participant_ids = set(chat_room.participants.values_list('id', flat=True))

            for p_id in new_participant_ids:
                try:
                    participant_to_add = User.objects.get(id=p_id)
                    if participant_to_add.id not in current_participant_ids:
                        chat_room.participants.add(participant_to_add)
                        current_participant_ids.add(participant_to_add.id) # Update current set to avoid re-adding if ID is duplicated in input
                        added_users_count += 1
                    # else: user is already in the group
                except User.DoesNotExist:
                    errors.append(f"Пользователь с ID {p_id} не найден.")
            
            if errors:
                # Decide if partial success is okay or if it should be all or nothing.
                # For now, return errors if any user ID was invalid.
                return JsonResponse({'status': 'error', 'message': 'Не удалось добавить некоторых участников.', 'errors': errors}, status=400)

            if added_users_count > 0:
                chat_room.last_message_at = timezone.now() # Update to reflect activity
                chat_room.save()
                return JsonResponse({'status': 'success', 'message': f'Успешно добавлено {added_users_count} новых участников.'})
            else:
                return JsonResponse({'status': 'info', 'message': 'Новых участников не было добавлено (возможно, они уже в группе).'}, status=200)

        except ChatRoom.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Групповой чат не найден.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Неверный формат JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Error adding participants to group chat (room_id={room_id}, user_id={request.user.id}): {e}")
            return JsonResponse({'status': 'error', 'message': 'Произошла ошибка при добавлении участников в группу.'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Метод не разрешен. Требуется POST.'}, status=405)