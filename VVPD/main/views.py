from django.http import HttpResponse
from django.shortcuts import render
from datetime import datetime



def index_page(request):
    return render(request, 'indexPage.html')

def second_page(request):
    return render(request, 'SecondPage.html')