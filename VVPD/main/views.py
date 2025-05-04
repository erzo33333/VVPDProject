from django.http import HttpResponse
from datetime import datetime
from main.models import User, Event
from django.shortcuts import render, redirect
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
    return render(request, 'MainPage.html', context={})


@login_required(login_url='login')
def index_page(request):
    return render(request, 'IndexPage.html', context={})


#@login_required(login_url='login')
def second_page(request):
    return render(request, 'SecondPage.html', context={})