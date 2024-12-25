from django.shortcuts import render, HttpResponse,redirect
from .models import UserInfo
# Create your views here.

def index(request):
    return HttpResponse("请求路径:{}" .format(request.path))

def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username == "admin" and password == "123456":
            return HttpResponse("登录成功")
        else:
            return render(request, 'login.html', {'error_message': "用户名或密码错误"})

def tql(request):
    name = "wangshuo"
    role = ["admin", "user", "guest"]
    return render(request, 'tql.html', {'name': name, 'role': role})

def test(request):
    print(request.method)
    print(request.GET)

    return redirect('/tql/')

def singup(request):
    return render(request, 'singup.html')

def user(request):
    UserInfo.objects.create(username="admin", password="123456", age=18)
    return HttpResponse("用户信息")
