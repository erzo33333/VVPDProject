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
            'StartTime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'EndTime': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'Description': forms.Textarea(attrs={'rows': 4}),
            'Colour': forms.TextInput(attrs={'placeholder': 'Цвет события (например: blue)'}),
        }
