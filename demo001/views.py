from django.shortcuts import render, HttpResponse,redirect
from .models import UserInfo
from functools import wraps
from django.contrib import messages
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.http import JsonResponse
import os
from django.conf import settings
import subprocess
import threading
import re

# 添加全局变量用于存储模拟进程和输出
simulation_processes = {}
simulation_outputs = {}

# 在文件开头添加系统类型到原子类型的映射
SYSTEM_ATOM_TYPES = {
    'water': ['O', 'H'],
    'methane': ['C', 'H'],
    'copper': ['Cu'],
    # 可以继续添加其他系统类型
}

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
    # 清理用户的模拟进程
    user_id = request.session.get('user_id')
    if user_id in simulation_processes:
        process = simulation_processes[user_id]
        if process.poll() is None:  # 如果进程还在运行
            process.terminate()  # 终止进程
        del simulation_processes[user_id]
    if user_id in simulation_outputs:
        del simulation_outputs[user_id]
    
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

def get_system_files():
    """获取分子系统数据集文件列表"""
    md_sys_path = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/md_sys'
    system_files = []
    
    try:
        for file in os.listdir(md_sys_path):
            if file.endswith('.lmp'):
                # 将文件名中的空格替换为下划线
                safe_name = file.replace(' ', '_')
                if safe_name != file:
                    # 如果文件名包含空格，重命名文件
                    old_path = os.path.join(md_sys_path, file)
                    new_path = os.path.join(md_sys_path, safe_name)
                    os.rename(old_path, new_path)
                    file = safe_name
                
                system_files.append({
                    'value': file,
                    'name': file
                })
    except Exception as e:
        system_files = [{'value': 'water.lmp', 'name': 'water.lmp'}]
    
    return system_files

@login_required
def analysis(request):
    # 获取分子系统类型（目录名）
    model_path = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/model'
    system_types = []
    
    try:
        for item in os.listdir(model_path):
            if os.path.isdir(os.path.join(model_path, item)):
                system_types.append({
                    'value': item,
                    'name': item
                })
    except Exception as e:
        system_types = []
    
    context = {
        'system_types': system_types,
        'system_files': get_system_files(),
        'atom_types_map': SYSTEM_ATOM_TYPES  # 传递原子类型映射到模板
    }
    return render(request, 'analysis.html', context)

@login_required
def get_deepmd_models(request):
    """获取指定系统类型下的深度势能模型列表"""
    system_type = request.GET.get('system_type')
    models = []
    
    if system_type:
        model_dir = f'/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/model/{system_type}'
        try:
            for file in os.listdir(model_dir):
                if file.endswith('.pb'):
                    models.append({
                        'value': file,
                        'name': file
                    })
        except Exception as e:
            pass
    
    return JsonResponse({'models': models})

@login_required
def start_simulation(request):
    if request.method == 'POST':
        try:
            # 确保输出目录存在
            output_dir = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output'
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取选择的分子系统
            selected_system = request.POST.get('system', 'water.lmp')
            system_path = f'/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/md_sys/{selected_system}'
            
            # 获取选择的系统类型和模型
            system_type = request.POST.get('system_type')
            model = request.POST.get('deepmd_model')
            model_path = f'/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/model/{system_type}/{model}'
            
            # 获取系统对应的原子类型
            atom_types = SYSTEM_ATOM_TYPES.get(system_type, [''])
            pair_coeff = f"pair_coeff      * * {' '.join(atom_types)}"
            
            # 获取原子质量和类型配置
            masses = request.POST.getlist('mass[]')
            atom_types = request.POST.getlist('atom_type[]')
            
            # 构建质量配置和group配置
            mass_config = []
            group_config = []
            
            for i, (mass, atom_type) in enumerate(zip(masses, atom_types), 1):
                mass_config.append(f'mass            {i} {mass}    # {atom_type}')
                group_config.append(f'group       {atom_type}  type {i}')
            
            mass_config = '\n'.join(mass_config)
            group_config = '\n'.join(group_config)
            
            # 生成LAMMPS输入文件
            input_content = f"""# Molecular dynamics simulation

units           {request.POST.get('units', 'metal')}
boundary        {request.POST.get('boundary', 'p p p')}
atom_style      atomic

neighbor        2.0 bin
neigh_modify    every 10 delay 0 check no

read_data       {system_path}
{mass_config}

# 定义原子组
{group_config}

pair_style      deepmd  {model_path}
{pair_coeff}

velocity        all create {request.POST.get('temperature', '330.0')} 23456789

fix             1 all nvt temp {request.POST.get('temperature', '330.0')} {request.POST.get('temperature', '330.0')} 0.5
timestep        {request.POST.get('timestep', '0.0005')}
thermo_style    custom step pe ke etotal temp press vol
thermo          {request.POST.get('thermo', '100')}
"""

            # 检查是否启用轨迹输出
            if request.POST.get('enableDump') == 'on':
                input_content += f"""
#输出轨迹
dump            1 all custom {request.POST.get('dump', '100')} {output_dir}/dump/Dump.dump id type x y z
"""

            # 检查是否启用原子力输出
            if request.POST.get('enableForce') == 'on':
                force_dump_frequency = request.POST.get('forceDump', '100')  # 获取用户输入的原子力输出频率
                input_content += f"""
#输出力
compute myForce all property/atom fx fy fz
dump 2 all custom {force_dump_frequency} {output_dir}/force/Force.dump id type c_myForce[1] c_myForce[2] c_myForce[3]
"""

            # 检查是否启用RDF计算
            if request.POST.get('enableRDF') == 'on':
                rdf_sample_frequency = request.POST.get('rdfSample', '100')  # 获取用户输入的RDF采样频率
                rdf_dump_frequency = request.POST.get('rdfDump', '100')  # 获取用户输入的RDF输出频率
                
                # 生成RDF原子对
                num_atom_types = len(atom_types)
                rdf_pairs = []
                for i in range(1, num_atom_types + 1):
                    for j in range(i, num_atom_types + 1):
                        rdf_pairs.append(f"{i} {j}")
                
                rdf_pairs_str = f"" + " ".join(rdf_pairs)
                
                input_content += f"""
#输出RDF
compute rdf all rdf 100 {rdf_pairs_str}
fix 2 all ave/time {rdf_sample_frequency} 1 {rdf_dump_frequency} c_rdf[*] file {output_dir}/rdf/RDF.rdf mode vector
"""

            input_content += f"""
run             {request.POST.get('runsteps', '1000')}
"""

            # 保存输入文件
            input_file = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/inLammps/in.lammps'
            with open(input_file, 'w') as f:
                f.write(input_content)
            
            # 启动LAMMPS进程
            lmp_path = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/lmp'
            process = subprocess.Popen(
                [lmp_path, '-in', input_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd='/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps'
            )
            
            # 存储进程信息
            user_id = request.session['user_id']
            simulation_processes[user_id] = process
            simulation_outputs[user_id] = {
                'output': '',
                'progress': 0,
                'total_steps': int(request.POST.get('runsteps', 1000))
            }
            
            # 启动输出监控线程
            threading.Thread(
                target=monitor_simulation_output,
                args=(user_id,),
                daemon=True
            ).start()
            
            return JsonResponse({'status': 'started'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
def get_simulation_output(request):
    user_id = request.session['user_id']
    
    if user_id not in simulation_outputs:
        return JsonResponse({
            'status': 'error',
            'message': '没有运行中的模拟'
        })
    
    sim_data = simulation_outputs[user_id]
    process = simulation_processes.get(user_id)
    
    # 格式化输出数据
    formatted_output = {
        'setup': sim_data['output']['setup'],
        'progress': sim_data['output']['progress'],
        'performance': sim_data['output']['performance']
    }
    
    if process is None or process.poll() is not None:
        # 进程已结束
        if user_id in simulation_processes:
            del simulation_processes[user_id]
        return JsonResponse({
            'status': 'completed',
            'output': formatted_output,
            'progress': 100
        })
    
    return JsonResponse({
        'status': 'running',
        'output': formatted_output,
        'progress': sim_data['progress']
    })

def monitor_simulation_output(user_id):
    """监控模拟进程的输出"""
    process = simulation_processes[user_id]
    sim_data = simulation_outputs[user_id]
    total_steps = sim_data['total_steps']
    
    # 初始化输出结构
    sim_data['output'] = {
        'setup': [],      # 设置信息
        'progress': [],   # 进度信息
        'performance': [] # 性能信息
    }
    
    # 定义不同类型信息的模式
    patterns = {
        'setup': [
            'Setting up',
            'Unit style',
            'Current step',
            'Time step',
            'Per MPI rank memory allocation'
        ],
        'progress': [
            'Step PotEng',
            r'^\s+\d+\s+[-\d.]+'  # 匹配数据行
        ],
        'performance': [
            'Loop time of',
            'Performance:',
            r'^\d+\.\d+% CPU',    # CPU使用率
            'MPI task timing breakdown:',
            r'Section\s+\|',      # 表头
            r'Pair\s+\|',         # 各项性能指标
            r'Neigh\s+\|',
            r'Comm\s+\|',
            r'Output\s+\|',
            r'Modify\s+\|',
            r'Other\s+\|',
            'Total # of neighbors',
            'Ave neighs/atom',
            'Neighbor list builds',
            'Total wall time:'
        ]
    }
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        
        # 分类处理不同类型的输出信息
        for output_type, pattern_list in patterns.items():
            if any(re.search(pattern, line) for pattern in pattern_list):
                sim_data['output'][output_type].append(line.strip())
                break
        
        # 更新进度
        if 'Step' in line:
            try:
                current_step = int(re.search(r'Step\s+(\d+)', line).group(1))
                sim_data['progress'] = min(100, int(current_step * 100 / total_steps))
            except:
                pass
    
    # 处理剩余输出
    remaining_output = process.stdout.read()
    if remaining_output:
        for line in remaining_output.splitlines():
            for output_type, pattern_list in patterns.items():
                if any(re.search(pattern, line) for pattern in pattern_list):
                    sim_data['output'][output_type].append(line.strip())
                    break

