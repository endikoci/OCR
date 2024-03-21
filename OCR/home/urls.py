from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/upload/', views.file_upload, name='file_upload'),
    
]