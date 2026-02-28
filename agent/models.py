from django.db import models
# agent/models.py
from django.db import models

class ScholarshipCategory(models.Model):
    name = models.CharField(max_length=100, unique=True) # e.g., "msbte", "medical"

    def __str__(self):
        return self.name

class VerifiedScholarship(models.Model):
    category = models.ForeignKey(ScholarshipCategory, on_delete=models.CASCADE, related_name='scholarships')
    title = models.CharField(max_length=255)
    # UNIQUE=TRUE is the magic bullet that prevents duplicate scholarships!
    url = models.URLField(unique=True, max_length=500) 
    source = models.CharField(max_length=100, blank=True, null=True)
    
    # Trust Engine Data
    trust_score = models.IntegerField()
    status = models.CharField(max_length=50)
    security_flags = models.JSONField(default=list)
    
    # Rich Extracted Data
    deadline = models.CharField(max_length=50, blank=True, null=True)
    info_paragraph = models.TextField()
    documents_required = models.JSONField(default=list)
    
    # Tracking
    added_from = models.CharField(max_length=50, default="RSS") # e.g., "WhatsApp", "RSS", "Manual"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.trust_score}] {self.title}"
class ScholarshipLead(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Analysis'),
        ('VERIFIED', 'Verified Safe'),
        ('SCAM', 'Potential Scam'),
    ]

    title = models.CharField(max_length=500)
    url = models.URLField(unique=True)
    source = models.CharField(max_length=100) # e.g., "Google News", "Manual Submission"
    
    # The "Property Card" Data (Extracted by your script)
    income_limit = models.CharField(max_length=100, blank=True, null=True)
    deadline = models.CharField(max_length=100, blank=True, null=True)
    
    # Security Data
    trust_score = models.IntegerField(default=0)
    red_flags = models.TextField(blank=True) # Store reasons why it might be a scam
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.status}] {self.title}"