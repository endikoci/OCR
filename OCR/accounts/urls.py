# accounts/urls.py
from django.urls import path
from . import views
from django.urls import include

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
]
