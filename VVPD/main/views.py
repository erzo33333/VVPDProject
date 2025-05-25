from django.http import HttpResponse, JsonResponse
import datetime # ADDED: Ensure datetime module is imported
from main.models import User, Event, UserProfile
from django.shortcuts import render, redirect, get_object_or_404
from .forms import LoginForm, RegistrationForm, UserEditForm, UserProfileForm, EventForm
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required
import logging # Import the logging module
from django.contrib import messages # For feedback messages
from django.contrib.auth import get_user_model
from django.core.serializers import serialize
import json
from django.db.models import Q

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
                return redirect('main page')
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
            event = form.save(commit=False)
            event.Creator = request.user
            event.save()
            # Participants are added by default if it's the creator
            # event.Participants.add(request.user) # Already handled if Creator is set and model is structured well
            messages.success(request, 'Событие успешно создано!')
            return redirect('main_page') # Or to a specific event detail page
        else:
            # Pass the form with errors back to the template, ideally via AJAX to the modal
            # For now, just add error messages and redirect, or render main_page with errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{form.fields[field].label if field in form.fields else field}': {error}")
            # Consider rendering the main_page with the invalid form to show errors in the modal
            # This would require passing form back and handling it in JS to re-populate modal
            # For simplicity now, redirecting and showing messages.
            return redirect('main_page') 
    else:
        # GET request not typically used for create_event directly this way
        # Modal is usually populated and submitted by JS
        return redirect('main_page')


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
    # Fetch events that are active on the target_date
    # An event is active if its StartTime (date part) <= target_date AND EndTime (date part) >= target_date
    events = Event.objects.filter(
        Q(Creator=request.user), # Or Q(Participants=request.user) if they should see events they are part of
        Q(StartTime__date__lte=target_date),
        Q(EndTime__date__gte=target_date)
    ).distinct().order_by('StartTime')

    event_list = []
    for event in events:
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
    event_instance = get_object_or_404(Event, id=event_id, Creator=request.user)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event_instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Событие успешно обновлено!')
            return redirect('main_page')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Ошибка в поле '{form.fields[field].label if field in form.fields else field}': {error}")
            # Ideally, handle errors more gracefully with modals, perhaps via AJAX
            # For now, redirecting back with messages. The modal won't show the errors directly unless JS is updated.
            return redirect('main_page') 
    else:
        # This case (GET request to edit_event) might not be hit if modal is populated by JS
        # But if it were, you'd pass the form to a template.
        return redirect('main_page') # Or render a specific edit page/modal