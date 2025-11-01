from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template import Context, Template
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from judge.models.emailing import BulkEmailCampaign, EmailRecipient, EmailLog, EmailTemplate
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_bulk_email_campaign(self, campaign_id):
    """
    Celery task to send bulk email campaign asynchronously.
    
    Args:
        campaign_id: ID of the BulkEmailCampaign to process
    """
    try:
        campaign = BulkEmailCampaign.objects.get(id=campaign_id)
        campaign.mark_as_processing()
        
        logger.info(f"Starting bulk email campaign: {campaign.name}")
        
        # Get all pending recipients
        recipients = EmailRecipient.objects.filter(
            campaign=campaign,
            status='pending'
        ).select_related('campaign')
        
        sent_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                # Validate email
                validate_email(recipient.email)
                
                # Prepare email content
                subject = campaign.subject
                body = campaign.body
                
                # Basic template variable replacement if extra_data exists
                if recipient.extra_data:
                    try:
                        subject_template = Template(subject)
                        body_template = Template(body)
                        context = Context(recipient.extra_data)
                        subject = subject_template.render(context)
                        body = body_template.render(context)
                    except Exception as e:
                        logger.warning(f"Template rendering failed for {recipient.email}: {e}")
                        # Continue with original content
                
                # Send email
                send_single_email.delay(
                    recipient.id,
                    recipient.email,
                    subject,
                    body,
                    campaign.is_html,
                    campaign.created_by.id if campaign.created_by else None
                )
                
                # Note: We'll let send_single_email handle success/failure tracking
                # Count will be updated after all emails are processed
                    
            except ValidationError:
                # Invalid email address
                recipient.status = 'invalid'
                recipient.error_message = "Invalid email address format"
                recipient.save()
                failed_count += 1
                logger.warning(f"Invalid email address: {recipient.email}")
                
            except Exception as e:
                # Other errors
                recipient.mark_as_failed(str(e))
                failed_count += 1
                logger.error(f"Error processing recipient {recipient.email}: {e}")
        
        # Update campaign statistics by counting actual recipient statuses
        # Note: Individual email tasks will update these counts as they complete
        # We'll mark the campaign as completed when all emails are processed
        
        logger.info(f"Queued bulk email campaign: {campaign.name}. "
                   f"Total recipients: {recipients.count()}")
        
        # Schedule a task to check completion status after a delay
        check_campaign_completion.apply_async(args=[campaign_id], countdown=60)
        
        return {
            'campaign_id': campaign_id,
            'total_queued': recipients.count(),
            'status': 'processing'
        }
        
    except BulkEmailCampaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
        raise
        
    except Exception as e:
        logger.error(f"Error in bulk email campaign {campaign_id}: {e}")
        # Mark campaign as failed
        try:
            campaign = BulkEmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.error_message = str(e)
            campaign.completed_at = timezone.now()
            campaign.save()
        except:
            pass
        raise


@shared_task(bind=True, max_retries=3)
def send_single_email(self, recipient_id, email_address, subject, body, is_html=True, sent_by_id=None):
    """
    Celery task to send a single email.
    
    Args:
        recipient_id: ID of EmailRecipient record
        email_address: Email address to send to
        subject: Email subject
        body: Email body content
        is_html: Whether body is HTML
        sent_by_id: ID of user who initiated the send
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        recipient = EmailRecipient.objects.get(id=recipient_id)
        
        # Send the email
        send_mail(
            subject=subject,
            message=body if not is_html else '',
            html_message=body if is_html else None,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_address],
            fail_silently=False,
        )
        
        # Mark recipient as sent
        recipient.mark_as_sent()
        
        # Update campaign statistics
        campaign = recipient.campaign
        campaign.emails_sent = EmailRecipient.objects.filter(campaign=campaign, status='sent').count()
        campaign.emails_failed = EmailRecipient.objects.filter(campaign=campaign, status__in=['failed', 'invalid']).count()
        campaign.save(update_fields=['emails_sent', 'emails_failed'])
        
        # Check if all emails are processed and mark campaign as completed if so
        pending_count = EmailRecipient.objects.filter(campaign=campaign, status='pending').count()
        if pending_count == 0 and campaign.status == 'processing':
            campaign.mark_as_completed()
            logger.info(f"Campaign {campaign.name} completed. Sent: {campaign.emails_sent}, Failed: {campaign.emails_failed}")
        
        # Log the email
        EmailLog.objects.create(
            email_type='bulk_campaign',
            recipient_email=email_address,
            subject=subject,
            campaign=recipient.campaign,
            template=recipient.campaign.template,
            sent_by_id=sent_by_id,
            is_successful=True
        )
        
        logger.info(f"Email sent successfully to {email_address}")
        return True
        
    except EmailRecipient.DoesNotExist:
        logger.error(f"Recipient {recipient_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"Failed to send email to {email_address}: {e}")
        
        # Mark recipient as failed
        try:
            recipient = EmailRecipient.objects.get(id=recipient_id)
            recipient.mark_as_failed(str(e))
            
            # Update campaign statistics
            campaign = recipient.campaign
            campaign.emails_sent = EmailRecipient.objects.filter(campaign=campaign, status='sent').count()
            campaign.emails_failed = EmailRecipient.objects.filter(campaign=campaign, status__in=['failed', 'invalid']).count()
            campaign.save(update_fields=['emails_sent', 'emails_failed'])
            
            # Check if all emails are processed and mark campaign as completed if so
            pending_count = EmailRecipient.objects.filter(campaign=campaign, status='pending').count()
            if pending_count == 0 and campaign.status == 'processing':
                campaign.mark_as_completed()
                logger.info(f"Campaign {campaign.name} completed. Sent: {campaign.emails_sent}, Failed: {campaign.emails_failed}")
        except:
            pass
        
        # Log the failure
        try:
            EmailLog.objects.create(
                email_type='bulk_campaign',
                recipient_email=email_address,
                subject=subject,
                sent_by_id=sent_by_id,
                is_successful=False,
                error_message=str(e)
            )
        except:
            pass
        
        return False


@shared_task
def check_campaign_completion(campaign_id):
    """
    Check if a campaign is completed and mark it accordingly.
    This task is scheduled to run after individual email tasks have had time to complete.
    """
    try:
        campaign = BulkEmailCampaign.objects.get(id=campaign_id)
        
        # Skip if campaign is already completed or failed
        if campaign.status in ['sent', 'failed', 'partially_sent']:
            return
            
        # Count pending emails
        pending_count = EmailRecipient.objects.filter(campaign=campaign, status='pending').count()
        
        if pending_count == 0:
            # All emails have been processed, mark campaign as completed
            campaign.mark_as_completed()
            logger.info(f"Campaign {campaign.name} marked as completed. "
                       f"Sent: {campaign.emails_sent}, Failed: {campaign.emails_failed}")
        else:
            # Some emails are still pending, schedule another check
            logger.info(f"Campaign {campaign.name} still has {pending_count} pending emails, checking again later")
            check_campaign_completion.apply_async(args=[campaign_id], countdown=30)
            
    except BulkEmailCampaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found for completion check")


@shared_task
def send_template_test_email(template_id, recipient_email, sent_by_id):
    """
    Task to send a test email using a template.
    
    Args:
        template_id: ID of EmailTemplate to use
        recipient_email: Email address to send test to
        sent_by_id: ID of user sending the test
    """
    try:
        template = EmailTemplate.objects.get(id=template_id)
        
        # Send test email
        send_mail(
            subject=f"[TEST] {template.subject}",
            message=template.body if not template.is_html else '',
            html_message=template.body if template.is_html else None,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        # Log the test email
        EmailLog.objects.create(
            email_type='template_test',
            recipient_email=recipient_email,
            subject=f"[TEST] {template.subject}",
            template=template,
            sent_by_id=sent_by_id,
            is_successful=True
        )
        
        logger.info(f"Test email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        
        # Log the failure
        try:
            EmailLog.objects.create(
                email_type='template_test',
                recipient_email=recipient_email,
                subject=f"[TEST] Template Test",
                sent_by_id=sent_by_id,
                is_successful=False,
                error_message=str(e)
            )
        except:
            pass
        
        return False


@shared_task
def cleanup_old_email_logs(days=30):
    """
    Task to cleanup old email logs.
    
    Args:
        days: Number of days to keep logs (default: 30)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    deleted_count = EmailLog.objects.filter(sent_at__lt=cutoff_date).count()
    EmailLog.objects.filter(sent_at__lt=cutoff_date).delete()
    
    logger.info(f"Cleaned up {deleted_count} old email log entries")
    return deleted_count


@shared_task
def cleanup_old_campaigns(days=90):
    """
    Task to cleanup old completed campaigns and their files.
    
    Args:
        days: Number of days to keep completed campaigns (default: 90)
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    old_campaigns = BulkEmailCampaign.objects.filter(
        completed_at__lt=cutoff_date
    )
    
    deleted_count = 0
    for campaign in old_campaigns:
        # Delete uploaded file if it exists
        if campaign.uploaded_file:
            try:
                campaign.uploaded_file.delete(save=False)
            except:
                pass
        deleted_count += 1
    
    # Delete campaigns and their related recipients
    old_campaigns.delete()
    
    logger.info(f"Cleaned up {deleted_count} old email campaigns")
    return deleted_count