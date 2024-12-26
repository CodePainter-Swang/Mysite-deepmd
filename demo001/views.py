from django.shortcuts import render, HttpResponse,redirect
from .models import UserInfo
# Create your views here.



def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = UserInfo.objects.filter(username=username, password=password).first()
        if user:
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            return redirect("/index/")
        else:
            return render(request, 'login.html', {'error_message': "用户名或密码错误"})

def singup(request):
    if request.method == "GET":
        return render(request, 'singup.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        UserInfo.objects.create(username=username, password=password, email=email, phone=phone)
        return HttpResponse("注册成功")

def user(request):
    UserInfo.objects.create(username="admin", password="123456", age=18)
    return HttpResponse("用户信息")

def index(request):
    if not request.session.get('user_id'):
        return redirect('demo001:login')
    return render(request, 'index.html')

def logout(request):
    request.session.flush()
    return redirect('demo001:login')
