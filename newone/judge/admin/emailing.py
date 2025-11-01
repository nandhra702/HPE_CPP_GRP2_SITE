from django.contrib import admin
from django.contrib.admin import helpers
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.core.exceptions import PermissionDenied
from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.utils.safestring import mark_safe
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
import csv
import io
from judge.models.emailing import EmailTemplate, BulkEmailCampaign, EmailRecipient, EmailLog

# Optional pandas import for Excel support
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class EmailTemplateForm(forms.ModelForm):
    """Custom form for email templates with rich text editor."""
    
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'body', 'is_html', 'is_active']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].widget = forms.Textarea(attrs={
            'rows': 15,
            'cols': 80,
            'class': 'vLargeTextField'
        })
        self.fields['subject'].widget.attrs.update({'size': 80})


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    form = EmailTemplateForm
    list_display = ['name', 'subject', 'is_html', 'is_active', 'created_at', 'created_by']
    list_filter = ['is_html', 'is_active', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']
    
    change_list_template = 'admin/emailing/templates_changelist.html'
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'subject', 'is_active')
        }),
        ('Email Content', {
            'fields': ('body', 'is_html'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new template
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.created_by and obj.created_by != request.user and not request.user.is_superuser:
            readonly.extend(['name', 'subject', 'body'])
        return readonly


class BulkEmailUploadForm(forms.Form):
    """Form for uploading bulk email files and composing emails."""
    
    TEMPLATE_CHOICES = [('custom', 'Custom Email (write your own)')]
    
    # Campaign details
    campaign_name = forms.CharField(
        max_length=200,
        help_text="Name for this email campaign"
    )
    
    # Template selection
    template = forms.ChoiceField(
        choices=TEMPLATE_CHOICES,
        initial='custom',
        help_text="Select a template or write a custom email"
    )
    
    # File upload
    email_file = forms.FileField(
        help_text="Upload CSV or Excel file containing email addresses (Excel support requires pandas)"
    )
    email_column = forms.CharField(
        max_length=100,
        initial='email',
        help_text="Column name containing email addresses (e.g., 'email', 'Email', 'email_address')"
    )
    
    # Email content (for custom emails)
    subject = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={'size': 80})
    )
    body = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 15, 'cols': 80, 'class': 'vLargeTextField'})
    )
    is_html = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Check if email body contains HTML"
    )
    
    # Template editing option
    enable_template_editing = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Enable editing template content (experimental feature)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate template choices dynamically
        templates = EmailTemplate.objects.filter(is_active=True).values_list('id', 'name')
        self.fields['template'].choices = [('custom', 'Custom Email (write your own)')] + list(templates)
        
    def clean(self):
        cleaned_data = super().clean()
        template_id = cleaned_data.get('template')
        subject = cleaned_data.get('subject')
        body = cleaned_data.get('body')
        enable_editing = cleaned_data.get('enable_template_editing', False)
        
        if template_id == 'custom':
            if not subject:
                raise forms.ValidationError("Subject is required for custom emails.")
            if not body:
                raise forms.ValidationError("Email body is required for custom emails.")
        elif template_id and template_id != 'custom' and enable_editing:
            # Only validate subject/body if template editing is enabled
            if not subject:
                raise forms.ValidationError("Subject is required. Please select a template again if it didn't load properly.")
            if not body:
                raise forms.ValidationError("Email body is required. Please select a template again if it didn't load properly.")
        
        return cleaned_data


@admin.register(BulkEmailCampaign)
class BulkEmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'total_emails', 'emails_sent', 'emails_failed', 
                   'progress_display', 'created_at', 'created_by']
    list_filter = ['status', 'created_at', 'template']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'total_emails', 
                      'emails_sent', 'emails_failed', 'progress_percentage']
    ordering = ['-created_at']
    
    # Add custom button in the list view
    change_list_template = 'admin/emailing/bulk_campaign_changelist.html'
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'status', 'template')
        }),
        ('Email Content', {
            'fields': ('subject', 'body', 'is_html'),
            'classes': ('collapse',)
        }),
        ('File Information', {
            'fields': ('uploaded_file', 'email_column'),
            'classes': ('collapse',)
        }),
        ('Progress Tracking', {
            'fields': ('total_emails', 'emails_sent', 'emails_failed', 'progress_percentage'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        if obj.total_emails == 0:
            return "No emails"
        progress = obj.progress_percentage
        color = 'green' if obj.status == 'sent' else 'orange' if obj.status == 'processing' else 'red'
        progress_text = f"{progress:.1f}%"
        return format_html(
            '<div style="width:100px; background-color:#f0f0f0; border:1px solid #ccc;">'
            '<div style="width:{}%; background-color:{}; height:20px; text-align:center; color:white;">'
            '{}</div></div>',
            progress, color, progress_text
        )
    progress_display.short_description = 'Progress'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-send/', self.admin_site.admin_view(self.bulk_send_view), name='emailing_bulk_send'),
            path('get-template/<int:template_id>/', self.admin_site.admin_view(self.get_template_data), name='emailing_get_template'),
        ]
        return custom_urls + urls
        
    def bulk_send_view(self, request):
        """View for bulk email sending interface."""
        # Check permissions
        if not self.has_change_permission(request):
            raise PermissionDenied("You don't have permission to send bulk emails")
            
        if request.method == 'POST':
            form = BulkEmailUploadForm(request.POST, request.FILES)
            if form.is_valid():
                return self.process_bulk_email(request, form)
        else:
            form = BulkEmailUploadForm()
            
        context = {
            'title': 'Bulk Email Sending',
            'form': form,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        return render(request, 'admin/emailing/bulk_send.html', context)
    
    def get_template_data(self, request, template_id):
        """AJAX endpoint to get template data."""
        # Check permissions
        if not self.has_view_permission(request) and not self.has_change_permission(request):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied'
            }, status=403)
            
        try:
            template = EmailTemplate.objects.get(id=template_id, is_active=True)
            return JsonResponse({
                'success': True,
                'subject': template.subject,
                'body': template.body,
                'is_html': template.is_html,
            })
        except EmailTemplate.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            })
        
    def process_bulk_email(self, request, form):
        """Process the bulk email form and create campaign."""
        try:
            with transaction.atomic():
                # Create campaign
                campaign_data = {
                    'name': form.cleaned_data['campaign_name'],
                    'email_column': form.cleaned_data['email_column'],
                    'created_by': request.user,
                    'uploaded_file': form.cleaned_data['email_file'],
                }
                
                # Handle template or custom content
                template_id = form.cleaned_data['template']
                enable_editing = form.cleaned_data.get('enable_template_editing', False)
                
                if template_id != 'custom':
                    template = EmailTemplate.objects.get(id=template_id)
                    campaign_data.update({
                        'template': template,
                        'subject': template.subject if not enable_editing else form.cleaned_data['subject'],
                        'body': template.body if not enable_editing else form.cleaned_data['body'],
                        'is_html': template.is_html if not enable_editing else form.cleaned_data['is_html'],
                    })
                else:
                    campaign_data.update({
                        'subject': form.cleaned_data['subject'],
                        'body': form.cleaned_data['body'],
                        'is_html': form.cleaned_data['is_html'],
                    })
                
                campaign = BulkEmailCampaign.objects.create(**campaign_data)
                
                # Process uploaded file
                emails = self.extract_emails_from_file(
                    campaign.uploaded_file,
                    form.cleaned_data['email_column']
                )
                
                # Create recipient records
                recipients = []
                for email_data in emails:
                    email_addr = email_data.pop('email')  # Remove email from extra_data
                    recipients.append(EmailRecipient(
                        campaign=campaign,
                        email=email_addr,
                        extra_data=email_data
                    ))
                
                EmailRecipient.objects.bulk_create(recipients, ignore_conflicts=True)
                
                # Update campaign totals
                campaign.total_emails = len(recipients)
                campaign.save()
                
                # Queue the campaign for sending
                from judge.tasks.emailing import send_bulk_email_campaign
                send_bulk_email_campaign.delay(campaign.id)
                
                messages.success(
                    request,
                    f'Campaign "{campaign.name}" created successfully with {len(recipients)} recipients. '
                    f'Emails are being sent in the background.'
                )
                
                return redirect('admin:judge_bulkemailcampaign_changelist')
                
        except Exception as e:
            messages.error(request, f'Error creating campaign: {str(e)}')
            return self.bulk_send_view(request)
            
    def extract_emails_from_file(self, uploaded_file, email_column):
        """Extract email addresses and data from uploaded CSV/Excel file."""
        emails = []
        
        try:
            if uploaded_file.name.endswith('.csv'):
                # Read CSV file
                file_content = uploaded_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(file_content))
                for row in csv_reader:
                    if email_column in row and row[email_column].strip():
                        email_data = dict(row)
                        email_data['email'] = email_data[email_column].strip()
                        emails.append(email_data)
                        
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                # Read Excel file (requires pandas)
                if not HAS_PANDAS:
                    raise ValueError("Excel file support requires pandas. Please install pandas: pip install pandas openpyxl")
                
                df = pd.read_excel(uploaded_file)
                if email_column in df.columns:
                    for _, row in df.iterrows():
                        if pd.notna(row[email_column]) and str(row[email_column]).strip():
                            email_data = row.to_dict()
                            email_data['email'] = str(email_data[email_column]).strip()
                            # Convert any NaN values to empty strings
                            email_data = {k: (v if pd.notna(v) else '') for k, v in email_data.items()}
                            emails.append(email_data)
                else:
                    raise ValueError(f"Column '{email_column}' not found in Excel file")
            else:
                raise ValueError("Unsupported file format. Please upload CSV or Excel files.")
                
        except Exception as e:
            raise ValueError(f"Error processing file: {str(e)}")
            
        if not emails:
            raise ValueError(f"No valid email addresses found in column '{email_column}'")
            
        return emails
    
    def has_add_permission(self, request):
        # Disable the default add view since we use custom bulk send
        return False


@admin.register(EmailRecipient)
class EmailRecipientAdmin(admin.ModelAdmin):
    list_display = ['email', 'campaign', 'status', 'sent_at']
    list_filter = ['status', 'campaign', 'sent_at']
    search_fields = ['email', 'campaign__name']
    readonly_fields = ['campaign', 'email', 'status', 'sent_at', 'error_message', 'extra_data']
    ordering = ['-sent_at']
    
    change_list_template = 'admin/emailing/recipients_changelist.html'
    
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject_truncated', 'email_type', 'is_successful', 'sent_at', 'sent_by']
    list_filter = ['email_type', 'is_successful', 'sent_at']
    search_fields = ['recipient_email', 'subject']
    readonly_fields = ['email_type', 'recipient_email', 'subject', 'campaign', 'template', 
                      'sent_by', 'sent_at', 'is_successful', 'error_message']
    ordering = ['-sent_at']
    
    change_list_template = 'admin/emailing/logs_changelist.html'
    
    def subject_truncated(self, obj):
        return obj.subject[:50] + "..." if len(obj.subject) > 50 else obj.subject
    subject_truncated.short_description = 'Subject'
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser