from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

def index(request):
    return HttpResponse("请求路径:{}" .format(request.path))

def login(request):
    return render(request, 'login.html')