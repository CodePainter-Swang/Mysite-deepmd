from django.shortcuts import render, HttpResponse,redirect
from .models import UserInfo
from functools import wraps
from django.contrib import messages
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.http import JsonResponse
import os
from django.conf import settings

# Create your views here.

def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            print("未登录，重定向到登录页面")  # 添加调试信息
            return redirect('demo001:login')
        return func(request, *args, **kwargs)
    return wrapper

def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = UserInfo.objects.filter(username=username, password=password).first()
        if user:
            # 设置session
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            # 设置session过期时间（可选）
            request.session.set_expiry(86400)  # 24小时后过期
            return redirect('demo001:index')
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



@login_required
def index(request):
    # 添加调试信息
    print("当前用户ID:", request.session.get('user_id'))
    return render(request, 'index.html')

def logout(request):
    request.session.flush()
    return redirect('demo001:login')


@login_required
def profile(request):
    user = UserInfo.objects.get(id=request.session['user_id'])
    return render(request, 'profile.html', {'user': user})

@login_required
def update_profile(request):
    if request.method == 'POST':
        try:
            user = UserInfo.objects.get(id=request.session['user_id'])
            
            # 获取表单数据
            new_username = request.POST.get('username')
            new_email = request.POST.get('email')
            new_phone = request.POST.get('phone')
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # 检查用户名是否已被其他用户使用
            if new_username != user.username:
                if UserInfo.objects.filter(username=new_username).exists():
                    messages.error(request, '用户名已被使用')
                    return redirect('demo001:profile')
            
            # 更新基本信息
            user.username = new_username
            user.email = new_email
            user.phone = new_phone
            
            # 密码更新逻辑
            if current_password and new_password and confirm_password:
                if user.password != current_password:
                    messages.error(request, '当前密码错误')
                    return redirect('demo001:profile')
                
                if new_password != confirm_password:
                    messages.error(request, '新密码与确认密码不匹配')
                    return redirect('demo001:profile')
                
                if len(new_password) < 6:
                    messages.error(request, '密码长度不能少于6位')
                    return redirect('demo001:profile')
                
                user.password = new_password
            
            # 保存更新
            user.save()
            
            # 更新session中的用户名
            request.session['username'] = new_username
            
            messages.success(request, '个人信息更新成功')
            return redirect('demo001:profile')
            
        except UserInfo.DoesNotExist:
            messages.error(request, '用户不存在')
        except IntegrityError:
            messages.error(request, '保存失败，请检查输入信息')
        except Exception as e:
            messages.error(request, f'发生错误：{str(e)}')
    
    return redirect('demo001:profile')

def user_list(request):
    # 获取所有用户
    users_list = UserInfo.objects.all().order_by('-id')
    
    # 分页
    paginator = Paginator(users_list, 10)  # 每页显示10条
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    return render(request, 'users.html', {'users': users})

@login_required
def reset_user_password(request):
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        try:
            user = UserInfo.objects.get(id=user_id)
            user.password = "123456"
            user.save()
            return JsonResponse({
                'status': 'success',
                'message': f'用户 {user.username} 的密码已重置为123456'
            })
        except UserInfo.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '用户不存在'
            })
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
def delete_user(request):
    if request.method == "POST":
        user_id = request.POST.get('user_id')
        try:
            user = UserInfo.objects.get(id=user_id)
            username = user.username
            user.delete()
            return JsonResponse({
                'status': 'success',
                'message': f'用户 {username} 已被删除'
            })
        except UserInfo.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '用户不存在'
            })
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
def upload_file(request):
    if request.method == 'POST':
        if 'file' not in request.FILES:
            return render(request, 'upload.html', {
                'message': '请选择要上传的文件',
                'success': False
            })
        
        uploaded_file = request.FILES['file']
        
        # 确保目标目录存在
        upload_dir = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/inLammps'
        os.makedirs(upload_dir, exist_ok=True)
        
        # 构建文件保存路径
        file_path = os.path.join(upload_dir, uploaded_file.name)
        
        try:
            # 保存文件
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            return render(request, 'upload.html', {
                'message': '文件上传成功！',
                'success': True
            })
        except Exception as e:
            return render(request, 'upload.html', {
                'message': f'文件上传失败：{str(e)}',
                'success': False
            })
    
    return render(request, 'upload.html')
