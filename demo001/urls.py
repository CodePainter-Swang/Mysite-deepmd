from django.urls import path
from . import views

app_name = "demo001"
urlpatterns = [
    path('', views.login, name='login'),
    path('index/', views.index, name='index'),
    path('logout/', views.logout, name='logout'),
    path('singup/', views.singup, name='singup'),
    path('profile/', views.profile, name='profile'),
    path('users/', views.user_list, name='user_list'),
    path('update_profile/', views.update_profile, name='update_profile'),
    path('reset_user_password/', views.reset_user_password, name='reset_user_password'),
    path('delete_user/', views.delete_user, name='delete_user'),
    path('upload/', views.upload_file, name='upload_file'),
    path('analysis/', views.analysis, name='analysis'),
    path('start_simulation/', views.start_simulation, name='start_simulation'),
    path('get_simulation_output/', views.get_simulation_output, name='get_simulation_output'),
    path('get_deepmd_models/', views.get_deepmd_models, name='get_deepmd_models'),
    path('get_simulation_data/<str:data_type>/', views.get_simulation_data, name='get_simulation_data'),
    path('download_data/<str:data_type>/', views.download_data, name='download_data'),
]
