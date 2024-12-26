from django.urls import path
from . import views

app_name = "demo001"
urlpatterns = [
    path('index/', views.index, name='index'),
    path('', views.login, name='login'),
    path('user/', views.user, name='user'),
    path('singup/', views.singup, name='singup'),
]
