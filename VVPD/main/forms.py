from django import forms
from main.models import User
from django.contrib.auth import get_user_model
from .models import UserProfile, Event # Import UserProfile


class LoginForm(forms.Form):
    username = forms.CharField(label='Имя пользователя')
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')\


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Повторите пароль')

    class Meta:
        model = get_user_model()
        fields = ['username', 'email']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Пароли не совпадают')
        return cd.get('password2')

class UserEditForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(label='Фото профиля', required=False)
    # Make sure the labels match what user expects or remove them to use verbose_name from model
    # For privacy fields, widgets can be RadioSelect if preferred over Dropdown
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'privacy_schedule_visibility',
            'privacy_can_invite_to_event',
            'privacy_can_send_message',
            'privacy_profile_photo_visibility',
            'interface_language'
        ]
        # Example of using widgets if needed:
        # widgets = {
        #     'privacy_schedule_visibility': forms.Select(attrs={'class': 'your-css-class'}),
        # }

class EventForm(forms.ModelForm):
    StartTime = forms.DateTimeField(
        label='Время начала',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    )
    EndTime = forms.DateTimeField(
        label='Время окончания',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    )
    Description = forms.CharField(
        label='Описание',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False 
    )
    # We'll add privacy field later when the model is updated.
    # Participants will also be handled later.

    class Meta:
        model = Event
        fields = ['Title', 'StartTime', 'EndTime', 'Description', 'event_type', 'Colour']
        widgets = {
            'Colour': forms.TextInput(attrs={'type': 'color'}), # Optional: color picker
        }
        labels = {
            'Title': 'Название события',
            'event_type': 'Тип события',
            'Colour': 'Цвет (если не выбран, установится по типу)',
        }

    def clean_Description(self):
        description_text = self.cleaned_data.get('Description', '')
        if description_text.strip(): # If not empty or just whitespace
            return {"text": description_text.strip()}
        return {} # Return an empty dictionary for empty input, aligning with model's default=dict