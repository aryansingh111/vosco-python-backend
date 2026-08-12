from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_connection, name="test"),
    path('login/', views.login, name="login"),
    path('credentials/<str:company_id>/', views.manage_credentials, name="credentials"),
]