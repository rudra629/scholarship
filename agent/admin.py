from django.contrib import admin
from .models import ScholarshipLead

@admin.register(ScholarshipLead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'trust_score', 'income_limit')
    list_filter = ('status',)