from django.contrib import admin
from .models import ScholarshipLead
from django.contrib import admin
from .models import ScholarshipCategory, VerifiedScholarship

@admin.register(VerifiedScholarship)
class VerifiedScholarshipAdmin(admin.ModelAdmin):
    list_display = ('title', 'trust_score', 'category', 'added_from')
    list_filter = ('added_from', 'category', 'trust_score')
    search_fields = ('title', 'url')

admin.site.register(ScholarshipCategory)
@admin.register(ScholarshipLead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'trust_score', 'income_limit')
    list_filter = ('status',)