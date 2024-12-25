from django.urls import path
from . import views

app_name = "demo001"
urlpatterns = [
    path('index/', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('tql/', views.tql, name='tql'),
    path('test/', views.test, name='test'),
    path('user/', views.user, name='user'),
    path('singup/', views.singup, name='singup'),

]
