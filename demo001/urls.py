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
]
