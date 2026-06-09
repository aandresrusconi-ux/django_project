from django.urls import path
from .views import LoginView, RefreshView, DashboardView

urlpatterns = [
    path('login/',     LoginView.as_view(),     name='auth-login'),
    path('refresh/',   RefreshView.as_view(),   name='auth-refresh'),
    path('dashboard/', DashboardView.as_view(), name='auth-dashboard'),
]
