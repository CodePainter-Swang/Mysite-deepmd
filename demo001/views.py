from django.shortcuts import render, HttpResponse,redirect
from .models import UserInfo
from functools import wraps
from django.contrib import messages
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.http import JsonResponse, FileResponse
import os
from django.conf import settings
import subprocess
import threading
import re
from django.utils.encoding import escape_uri_path
import json
import numpy as np

# 添加全局变量用于存储模拟进程和输出
simulation_processes = {}
simulation_outputs = {}

# 在文件开头添加系统类型到原子类型的映射
SYSTEM_ATOM_TYPES = {
    'H2O': ['O', 'H'],
    'LiCl': ['Li', 'Cl'],
    'Cu': ['Cu'],
    'Ag': ['Ag'],
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
        upload_dir = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/md_sys'
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
            # 保存系统类型到session
            system_type = request.POST.get('system_type')
            request.session['system_type'] = system_type
            
            # 确保输出目录存在
            output_dir = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output'
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取选择的分子系统
            selected_system = request.POST.get('system', 'water.lmp')
            system_path = f'/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/md_sys/{selected_system}'
            
            # 获取选择的系统类型和模型
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

@login_required
def get_simulation_data(request, data_type):
    """获取模拟数据"""
    try:
        page = int(request.GET.get('page', 1))
        timestep = request.GET.get('timestep')
        items_per_page = int(request.GET.get('items_per_page', 100))
        
        # 确保文件存在且可读
        file_paths = {
            'trajectory': '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/dump/Dump.dump',
            'force': '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/force/Force.dump',
            'rdf': '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/RDF.rdf'
        }
        
        if data_type not in file_paths:
            return JsonResponse({'error': '无效的数据类型'}, status=400)
            
        file_path = file_paths[data_type]
        if not os.path.exists(file_path):
            return JsonResponse({'error': '数据文件不存在'}, status=404)
            
        if data_type == 'trajectory':
            data = read_dump_file(file_path, timestep, page, items_per_page)
        elif data_type == 'force':
            data = read_dump_file(file_path, timestep, page, items_per_page)
        elif data_type == 'rdf':
            data = read_rdf_file(file_path, timestep, page, items_per_page)
            
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def read_dump_file(file_path, timestep, page, items_per_page):
    """读取dump文件数据"""
    data = []
    total_items = 0
    timesteps = set()
    
    with open(file_path, 'r') as f:
        current_timestep = None
        reading_data = False
        items_count = 0
        
        for line in f:
            line = line.strip()
            if line.startswith('ITEM: TIMESTEP'):
                current_timestep = int(next(f).strip())
                timesteps.add(current_timestep)
                reading_data = False
            elif line.startswith('ITEM: NUMBER OF ATOMS'):
                total_items = int(next(f).strip())
            elif line.startswith('ITEM: ATOMS'):
                if str(current_timestep) == str(timestep):
                    reading_data = True
                    continue
            elif reading_data:
                items_count += 1
                if (page - 1) * items_per_page < items_count <= page * items_per_page:
                    values = line.split()
                    data.append(values)
    
    return {
        'data': data,
        'total_items': total_items,
        'timesteps': sorted(list(timesteps)),
        'total_pages': (total_items + items_per_page - 1) // items_per_page
    }

def read_rdf_file(file_path, timestep=None, page=1, items_per_page=100):
    """读取RDF文件数据"""
    data = []
    total_items = 0
    timesteps = set()
    current_timestep = None
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
        # 跳过头部注释
        data_start = 0
        for i, line in enumerate(lines):
            if line.startswith('# TimeStep'):
                data_start = i + 1
                break
        
        # 读取时间步和数据
        i = data_start
        while i < len(lines):
            if lines[i].startswith('#'):
                if current_timestep:
                    timesteps.add(current_timestep)
                current_timestep = int(lines[i+1].strip().split()[0])
                i += 2
                continue
                
            if str(current_timestep) == str(timestep) or not timestep:
                values = lines[i].strip().split()
                # 修改这里：只要有数据就添加，不要固定检查8列
                if values:  # 只要有数据就添加
                    data.append(values)
            i += 1
            
        if current_timestep:
            timesteps.add(current_timestep)
            
        total_items = len(data)
        
        # 分页
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        data = data[start_idx:end_idx]
    
    return {
        'data': data,
        'total_items': total_items,
        'timesteps': sorted(list(timesteps)),
        'total_pages': (total_items + items_per_page - 1) // items_per_page
    }

def download_data(request, data_type):
    """下载模拟数据文件"""
    file_paths = {
        'trajectory': '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/dump/Dump.dump',
        'force': '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/force/Force.dump',
        'rdf': '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/rdf/RDF.rdf'
    }
    
    file_names = {
        'trajectory': 'Dump.dump',
        'force': 'Force.dump',
        'rdf': 'RDF.rdf'
    }
    
    if data_type not in file_paths:
        return HttpResponse('Invalid data type', status=400)
        
    file_path = file_paths[data_type]
    if not os.path.exists(file_path):
        return HttpResponse('File not found', status=404)
        
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment; filename={escape_uri_path(file_names[data_type])}'
    return response

@login_required
def visualization(request):
    """可视化展示选择页面"""
    return render(request, 'visualization.html')

def parse_lammps_log():
    """解析LAMMPS日志文件获取模拟参数"""
    log_file = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/log.lammps'
    simulation_info = {
        'timestep': None,      # 时间步长
        'temperature': None,   # 模拟温度
        'num_atoms': None,     # 原子数量
    }
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # 查找时间步长
                if 'timestep' in line.lower():
                    try:
                        simulation_info['timestep'] = float(line.split()[-1])
                    except (ValueError, IndexError):
                        pass
                
                # 查找温度设置
                elif 'temperature' in line.lower() and simulation_info['temperature'] is None:
                    try:
                        simulation_info['temperature'] = float(line.split()[-1])
                    except (ValueError, IndexError):
                        pass
                
                # 查找原子数量
                elif 'atoms' in line.lower() and simulation_info['num_atoms'] is None:
                    try:
                        simulation_info['num_atoms'] = int(line.split()[0])
                    except (ValueError, IndexError):
                        pass
                
                # 如果所有信息都找到了，就退出循环
                if all(v is not None for v in simulation_info.values()):
                    break
    except Exception as e:
        print(f"Error reading log file: {e}")
    
    return simulation_info

@login_required
def visualization_trajectory(request):
    """原子轨迹可视化页面"""
    # 获取模拟参数
    simulation_info = parse_lammps_log()
    
    # 从session中获取系统类型
    system_type = request.session.get('system_type', 'H2O')
    
    # 获取对应的原子类型映射
    atom_types = SYSTEM_ATOM_TYPES.get(system_type, ['O', 'H'])
    
    # 创建原子类型到颜色的映射
    atom_colors = {
        'O': '#ff0000',   # 红色
        'H': '#0000ff',   # 蓝色
        'Li': '#800080',  # 紫色
        'Cl': '#00ff00',  # 绿色
        'Cu': '#ffa500',  # 橙色
        'Ag': '#c0c0c0',  # 银色
    }
    
    # 为每个原子类型生成颜色映射
    color_mapping = {i+1: atom_colors[atom_type] for i, atom_type in enumerate(atom_types)}
    
    # 为每个原子类型生成名称映射
    type_mapping = {i+1: atom_type for i, atom_type in enumerate(atom_types)}
    
    context = {
        'simulation_info': simulation_info,
        'system_type': system_type,
        'color_mapping': color_mapping,
        'type_mapping': type_mapping,
    }
    
    return render(request, 'visualization_trajectory.html', context)

@login_required
def visualization_rdf(request):
    """RDF曲线可视化页面"""
    return render(request, 'visualization_rdf.html')

@login_required
def get_trajectory_data(request):
    """获取轨迹数据的时间步长信息"""
    try:
        timesteps = []
        current_timestep = None
        
        with open('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/dump/Dump.dump', 'r') as f:
            for line in f:
                if line.startswith('ITEM: TIMESTEP'):
                    if current_timestep:
                        timesteps.append(current_timestep)
                    current_timestep = int(next(f))
            
            if current_timestep:
                timesteps.append(current_timestep)
        
        return JsonResponse({
            'status': 'success',
            'timesteps': sorted(timesteps)
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_timestep_data(request):
    """获取特定时间步长的原子位置数据"""
    timestep = request.GET.get('timestep')
    if timestep is None:
        return JsonResponse({
            'status': 'error',
            'message': 'No timestep provided'
        }, status=400)
    
    try:
        atoms = []
        current_timestep = None
        reading_atoms = False
        box_info_lines = 0  # 用于跟踪box信息行数
        
        with open('/work/wangs/Django-deepmd/mysite_deepmd/demo001/lammps/output/dump/Dump.dump', 'r') as f:
            for line in f:
                if line.startswith('ITEM: TIMESTEP'):
                    current_timestep = int(next(f))
                    reading_atoms = False
                    box_info_lines = 0
                    if str(current_timestep) == str(timestep):
                        continue
                
                elif str(current_timestep) == str(timestep):
                    if line.startswith('ITEM: NUMBER OF ATOMS'):
                        continue
                    elif line.startswith('ITEM: BOX BOUNDS'):
                        box_info_lines = 3  # 需要跳过的box信息行数
                        continue
                    elif box_info_lines > 0:
                        box_info_lines -= 1
                        continue
                    elif line.startswith('ITEM: ATOMS'):
                        reading_atoms = True
                        continue
                    elif reading_atoms and line.strip():
                        try:
                            values = line.strip().split()
                            if len(values) >= 5:  # 确保有足够的数据
                                atoms.append({
                                    'id': int(values[0]),
                                    'type': int(values[1]),
                                    'x': float(values[2]),
                                    'y': float(values[3]),
                                    'z': float(values[4])
                                })
                        except (ValueError, IndexError):
                            continue
                
                # 如果已经读取完当前时间步的数据，且不是初始状态，就退出循环
                elif reading_atoms and str(current_timestep) != str(timestep):
                    break
        
        return JsonResponse({
            'status': 'success',
            'timestep': timestep,
            'atoms': atoms
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def calculate_rdf(request):
    """处理RDF计算请求并返回数据"""
    if request.method == 'POST':
        system_type = request.POST.get('system')
        selected_types = request.POST.getlist('types[]')
        
        # 验证系统类型和RDF类型的合法性
        valid_systems = {
            'H2O': ['O-O', 'O-H', 'H-H'],
            'copper': ['Cu-Cu'],
            'methane': ['C-C', 'C-H', 'H-H']
        }
        
        if system_type not in valid_systems:
            return JsonResponse({'error': '无效的系统类型'}, status=400)
            
        for rdf_type in selected_types:
            if rdf_type not in valid_systems[system_type]:
                return JsonResponse({'error': f'无效的RDF类型: {rdf_type}'}, status=400)
        
        try:
            # 根据系统类型获取对应的模型路径
            model_path = os.path.join(settings.BASE_DIR, 'demo001', 'lammps', 'model', system_type)
            
            # 使用plot_rdf.py中的逻辑计算RDF
            rdf_data = {}
            for rdf_type in selected_types:
                r, g_r = calculate_rdf_for_type(system_type, rdf_type, model_path)
                rdf_data[rdf_type] = {
                    'r': r.tolist(),
                    'g_r': g_r.tolist()
                }
            
            return JsonResponse(rdf_data)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '不支持的请求方法'}, status=405)

@login_required
def get_available_systems(request):
    """获取model目录下可用的分子系统类型"""
    try:
        model_dir = os.path.join(settings.BASE_DIR, 'demo001', 'lammps', 'model')
        # 获取model目录下的所有子目录
        systems = [d for d in os.listdir(model_dir) 
                  if os.path.isdir(os.path.join(model_dir, d))]
        
        # 为每个系统定义其可用的RDF类型
        system_rdf_types = {
            'H2O': ['O-O', 'O-H', 'H-H'],
            'copper': ['Cu-Cu']
        }
        
        # 只返回实际存在的系统目录中已定义RDF类型的系统
        available_systems = {sys: system_rdf_types.get(sys, []) 
                           for sys in systems 
                           if sys in system_rdf_types}
        
        return JsonResponse({
            'status': 'success',
            'systems': available_systems
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def generate_rdf(request):
    """生成RDF曲线并返回图片路径"""
    if request.method == 'POST':
        try:
            # 获取用户选择的RDF类型
            selected_types = request.POST.getlist('types[]')
            if not selected_types:
                return JsonResponse({
                    'status': 'error',
                    'message': '请选择至少一种RDF类型'
                }, status=400)

            # 运行RDF绘图脚本
            script_path = '/work/wangs/Django-deepmd/mysite_deepmd/demo001/plugins/plot_rdf.py'
            subprocess.run(['python', script_path], check=True)
            
            # 只返回用户选择的RDF类型对应的图片URL
            type_to_file = {
                'O-O': '/static/rdf/fig1.png',
                'O-H': '/static/rdf/fig2.png',
                'H-H': '/static/rdf/fig3.png'
            }
            
            selected_urls = {
                rdf_type: type_to_file[rdf_type]
                for rdf_type in selected_types
                if rdf_type in type_to_file
            }
            
            return JsonResponse({
                'status': 'success',
                'image_urls': selected_urls
            })
        except subprocess.CalledProcessError as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({'status': 'error', 'message': '不支持的请求方法'}, status=405)

