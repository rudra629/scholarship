# agent/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Ensure name is exactly "dashboard"
    path('', views.dashboard_ui, name="dashboard"),
    path('api/search/', views.search_and_verify, name="api_search"),
    path('api/list/', views.get_verified_scholarships, name="api_list"),
]