from django.http import HttpResponse


def index(request):
    return HttpResponse('<h4>Текст из views (метод index)..<h4>')