# agent/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Ensure name is exactly "dashboard"
    path('', views.dashboard_ui, name="dashboard"),
    path('api/search/', views.search_and_verify, name="api_search"),
    path('api/verify/', views.api_verify_url, name='api_verify'),
    path('api/list/', views.get_verified_scholarships, name="api_list"),
    path('api/whatsapp/', views.whatsapp_webhook, name='whatsapp_webhook'),
    path('api/main-search/', views.api_main_site_search, name='api_main_site_search'),
]