from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import validate_email


class EmailTemplate(models.Model):
    """Model for storing email templates that can be reused for bulk emailing."""
    
    name = models.CharField(max_length=200, unique=True, help_text="Unique name for the template")
    subject = models.CharField(max_length=500, help_text="Email subject line")
    body = models.TextField(help_text="Email body content (HTML and plain text supported)")
    is_html = models.BooleanField(default=True, help_text="Whether the body contains HTML content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Whether this template is available for use")
    
    class Meta:
        verbose_name = "📝 Email Template"
        verbose_name_plural = "📝 Templates (Reusable Emails)"
        ordering = ['-updated_at']
        
    def __str__(self):
        return self.name


class BulkEmailCampaign(models.Model):
    """Model for tracking bulk email campaigns."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('sent', 'Sent'), 
        ('failed', 'Failed'),
        ('partially_sent', 'Partially Sent'),
    ]
    
    name = models.CharField(max_length=200, help_text="Campaign name for identification")
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True, 
                                help_text="Template used (if any)")
    subject = models.CharField(max_length=500, help_text="Email subject (overrides template if custom)")
    body = models.TextField(help_text="Email body (overrides template if custom)")
    is_html = models.BooleanField(default=True)
    
    # File information
    uploaded_file = models.FileField(upload_to='bulk_email_files/', null=True, blank=True)
    email_column = models.CharField(max_length=100, default='email', 
                                   help_text="Column name containing email addresses")
    
    # Campaign metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_emails = models.PositiveIntegerField(default=0)
    emails_sent = models.PositiveIntegerField(default=0)
    emails_failed = models.PositiveIntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True, help_text="Error details if campaign failed")
    
    class Meta:
        verbose_name = "📧 Send Bulk Emails"
        verbose_name_plural = "Bulk emailing"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
        
    @property
    def progress_percentage(self):
        """Calculate progress percentage for the campaign."""
        if self.total_emails == 0:
            return 0
        return (self.emails_sent / self.total_emails) * 100
        
    def mark_as_processing(self):
        """Mark campaign as processing and set start time."""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
        
    def mark_as_completed(self):
        """Mark campaign as completed based on success/failure counts."""
        self.completed_at = timezone.now()
        if self.emails_failed == 0:
            self.status = 'sent'
        elif self.emails_sent == 0:
            self.status = 'failed'
        else:
            self.status = 'partially_sent'
        self.save(update_fields=['status', 'completed_at'])


class EmailRecipient(models.Model):
    """Model to track individual email recipients in a campaign."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('invalid', 'Invalid Email'),
    ]
    
    campaign = models.ForeignKey(BulkEmailCampaign, on_delete=models.CASCADE, related_name='recipients')
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Additional data from uploaded file (stored as JSON)
    extra_data = models.JSONField(default=dict, blank=True, 
                                 help_text="Additional data from uploaded file for personalization")
    
    class Meta:
        verbose_name = "📧 Email Recipient"
        verbose_name_plural = "📊 Recipients (Individual Status)"
        unique_together = ['campaign', 'email']
        
    def __str__(self):
        return f"{self.email} - {self.get_status_display()}"
        
    def mark_as_sent(self):
        """Mark this recipient as successfully sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
        
    def mark_as_failed(self, error_message=""):
        """Mark this recipient as failed with optional error message."""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])


class EmailLog(models.Model):
    """Model for logging all email sending activities."""
    
    TYPE_CHOICES = [
        ('template_test', 'Template Test'),
        ('bulk_campaign', 'Bulk Campaign'),
        ('individual', 'Individual Email'),
    ]
    
    email_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=500)
    campaign = models.ForeignKey(BulkEmailCampaign, on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "📋 Email Log"
        verbose_name_plural = "📋 Logs (Complete History)"
        ordering = ['-sent_at']
        
    def __str__(self):
        status = "✓" if self.is_successful else "✗"
        return f"{status} {self.recipient_email} - {self.subject[:50]}"