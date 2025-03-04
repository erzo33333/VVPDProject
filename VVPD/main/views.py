from django.http import HttpResponse
from django.shortcuts import render
from uuid import uuid4


def index_page(request):
    return render(request, 'indexPage.html')

def second_page(request):
    return render(request, 'SecondPage.html')