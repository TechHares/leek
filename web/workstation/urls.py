from django.urls import path
from . import views

app_name = "workstation"
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
