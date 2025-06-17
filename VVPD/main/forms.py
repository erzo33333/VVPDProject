import json
from django import forms


from main.models import User, Event
from django.contrib.auth import get_user_model


class LoginForm(forms.Form):
    username = (forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={'placeholder': 'Телефон или адрес эл. почты'}))
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Введите пароль'})
    )


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Пароль')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Повторите пароль')

    class Meta:
        model = get_user_model()
        fields = ['username']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Пароли не совпадают')
        return cd.get('password2')

    def __init__(self, *args, **kwargs):
        super(forms.ModelForm, self).__init__(*args, **kwargs)
        self.fields['username'].help_text = ''


class EventForm(forms.ModelForm):
    StartTime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    )
    EndTime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    )

    class Meta:
        model = Event
        fields = ['Title', 'StartTime', 'EndTime', 'Description', 'Colour']
        labels = {
            'Title': 'Название события',
            'StartTime': 'Начало',
            'EndTime': 'Конец',
            'Description': 'Описание',
            'Colour': 'Цвет события (например: blue)',
        }
        widgets = {
            'Title': forms.TextInput(attrs={'placeholder': 'Название события'}),
            'Description': forms.Textarea(attrs={'rows': 4}),
            'Colour': forms.TextInput(attrs={'placeholder': 'Цвет события (например: blue)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Преобразуем даты в формат для datetime-local, чтобы при редактировании корректно показывались значения
        for field in ['StartTime', 'EndTime']:
            value = self.initial.get(field) or (self.instance and getattr(self.instance, field))
            if value:
                self.initial[field] = value.strftime('%Y-%m-%dT%H:%M')
