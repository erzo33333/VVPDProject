from django.http import HttpResponse
from django.shortcuts import render
from datetime import datetime
from main.models import User, Event


def main_page(request):
    return render(request, 'MainPage.html', context={})

def index_page(request):
    return render(request, 'IndexPage.html', context={})

def second_page(request):
    return render(request, 'SecondPage.html', context={})