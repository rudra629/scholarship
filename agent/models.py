from django.db import models

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