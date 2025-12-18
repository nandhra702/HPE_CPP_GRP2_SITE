from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.db import transaction
import json

from .sites import HPEAdminSite
from .forms import ContestParticipantUploadForm, HPEContestForm, HPEProblemForm, HPEMCQForm

from judge.models import Problem, MCQQuestion, Contest, ContestProblem, ContestMCQ, Profile
from judge.admin.problem import ProblemAdmin
from judge.admin.mcq import MCQQuestionAdmin
from judge.admin.contest import ContestAdmin, ContestForm, ContestProblemInline, ContestMCQInline

# Initialize the custom admin site
hpe_admin_site = HPEAdminSite(name='hpe_admin')

class HPEContestAdmin(ContestAdmin):
    form = HPEContestForm
    change_form_template = 'hpe_admin/contest_change_form.html'
    inlines = [ContestProblemInline, ContestMCQInline] # Added Inlines
    
    def get_form(self, request, obj=None, **kwargs):
        # We skip ContestAdmin.get_form because it assumes fields exist that we removed.
        # super(ContestAdmin, self) will resolve to NoBatchDeleteMixin -> SortableAdminBase -> VersionAdmin -> ModelAdmin
        form = super(ContestAdmin, self).get_form(request, obj, **kwargs)
        return form

    # Custom fieldsets as requested
    fieldsets = (
        (None, {'fields': ('key', 'name', 'description')}),
        (_('Access Control'), {'fields': ('authors', 'testers')}),
        (_('Tester Permissions'), {'fields': ('tester_see_submissions', 'tester_see_scoreboard')}),
        (_('Problems'), {'fields': ('dashboard_button', 'contest_problems_json', 'contest_mcqs_json', 'contest_randomization_json')}),
        (_('Scheduling'), {'fields': ('start_time', 'end_time', 'time_limit')}),
        (_('Participants'), {'fields': ('private_contestants', 'participants_csv')}), # Manual adding + CSV
        # CSV Upload will be handled via a custom button in the change_form template or action
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:contest_id>/upload-participants/', self.upload_participants_view, name='hpe_contest_upload_participants'),
            path('<int:contest_id>/send-invites/', self.send_invites_view, name='hpe_contest_send_invites'),
        ]
        return custom_urls + urls

    def save_related(self, request, form, formsets, change):
        # 1. Save Inlines (Standard Django behavior)
        admin.ModelAdmin.save_related(self, request, form, formsets, change)
        
        # 2. Rescore logic
        if not self._rescored and any(formset.has_changed() for formset in formsets):
            self._rescore(form.cleaned_data['key'])

        # 3. JSON Logic (Non-destructive / Merging)
        if 'contest_problems_json' in form.cleaned_data and form.cleaned_data['contest_problems_json']:
            try:
                problems_data = json.loads(form.cleaned_data['contest_problems_json'])
                normalized_problems = []
                for item in problems_data:
                    if isinstance(item, int): normalized_problems.append({'id': item})
                    else: normalized_problems.append(item)
                
                current_problems = {cp.problem_id: cp for cp in form.instance.contest_problems.all()}
                
                for i, p_item in enumerate(normalized_problems):
                    pid = int(p_item['id'])
                    points = p_item.get('points')
                    partial = p_item.get('partial', True)
                    is_pretested = p_item.get('is_pretested', False)
                    max_submissions = p_item.get('max_submissions')
                    output_prefix_override = p_item.get('output_prefix_override', 0)
                    
                    if pid in current_problems:
                        cp = current_problems[pid]
                        changed = False
                        if cp.order != i: cp.order = i; changed = True
                        if points is not None and cp.points != points: cp.points = points; changed = True
                        if changed: cp.save()
                    else:
                        prob = Problem.objects.get(id=pid)
                        ContestProblem.objects.create(
                            contest=form.instance,
                            problem=prob,
                            points=points if points is not None else prob.points,
                            partial=partial,
                            is_pretested=is_pretested,
                            max_submissions=max_submissions,
                            output_prefix_override=output_prefix_override,
                            order=i
                        )
            except Exception as e: pass

        if 'contest_mcqs_json' in form.cleaned_data and form.cleaned_data['contest_mcqs_json']:
            try:
                mcq_data = json.loads(form.cleaned_data['contest_mcqs_json'])
                normalized_mcqs = []
                for item in mcq_data:
                    if isinstance(item, int): normalized_mcqs.append({'id': item})
                    else: normalized_mcqs.append(item)

                current_mcqs = {cm.mcq_question_id: cm for cm in form.instance.contest_mcqs.all()}
                
                for i, m_item in enumerate(normalized_mcqs):
                    mid = int(m_item['id'])
                    points = m_item.get('points')
                    if mid in current_mcqs:
                        cm = current_mcqs[mid]
                        changed = False
                        if cm.order != i: cm.order = i; changed = True
                        if points is not None and cm.points != points: cm.points = points; changed = True
                        if changed: cm.save()
                    else:
                        mcq = MCQQuestion.objects.get(id=mid)
                        ContestMCQ.objects.create(
                            contest=form.instance,
                            mcq_question=mcq,
                            points=points if points is not None else mcq.points,
                            order=i
                        )
            except Exception as e: pass

        # 4. Handle Participant CSV Upload (Moved from save_model to ensure M2M persistence)
        if 'participants_csv' in request.FILES:
            csv_file = request.FILES['participants_csv']
            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                import csv
                reader = csv.reader(decoded_file)
                
                created_count = 0
                added_count = 0
                
                for row in reader:
                    if not row: continue
                    email = row[0].strip()
                    if not email or '@' not in email: continue
                    
                    email_val = row[0].strip()
                    if not email_val or '@' not in email_val: continue
                    
                    if len(row) > 1 and row[1].strip():
                         username = row[1].strip()
                    else:
                         username = email_val.split('@')[0]
                    
                    user, created = User.objects.get_or_create(
                        email=email_val,
                        defaults={'username': username}
                    )
                    
                    if created:
                        password = get_random_string(12)
                        user.set_password(password)
                        user.save()
                        Profile.objects.get_or_create(user=user)
                        created_count += 1
                    
                    profile = user.profile
                    # Use form.instance (obj)
                    if not form.instance.private_contestants.filter(id=profile.id).exists():
                        form.instance.private_contestants.add(profile)
                        added_count += 1
                
                if not form.instance.is_private and added_count > 0:
                    form.instance.is_private = True
                    form.instance.save()

                if added_count > 0:
                    self.message_user(request, f"Processed CSV: {created_count} accounts created, {added_count} participants added.", level=messages.SUCCESS)
                    
            except Exception as e:
                self.message_user(request, f"Error processing CSV: {e}", level=messages.ERROR)


    def upload_participants_view(self, request, contest_id):
        # ... kept for backward compatibility if needed, but primary method is now valid on save_model
        return redirect('hpe_admin:judge_contest_change', contest_id)

    def send_invites_view(self, request, contest_id):
        contest = get_object_or_404(Contest, id=contest_id)
        
        # Iterate private contestants
        count = 0
        failed_emails = []
        
        for profile in contest.private_contestants.all():
            user = profile.user
            if not user.email: continue
            
            # Reset Password
            new_password = get_random_string(12)
            user.set_password(new_password)
            user.save()
            
            # Send Email
            contest_url = request.build_absolute_uri(reverse('contest_view', args=[contest.key]))
            subject = f"Invitation to {contest.name}"
            message = f"""
Hello {user.username},

You have been invited to participate in the contest "{contest.name}".

Link: {contest_url}
Username: {user.username}
Password: {new_password}

Good luck!
            """
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                count += 1
            except Exception as e:
                failed_emails.append(f"{user.email}: {str(e)}")
        
        messages.success(request, f"Sent invites to {count} participants.")
        if failed_emails:
            messages.warning(request, f"Failed to send to {len(failed_emails)} participants: <br>" + "<br>".join(failed_emails))
            
        return redirect('hpe_admin:judge_contest_change', contest_id)


class HPEProblemAdmin(ProblemAdmin):
    form = HPEProblemForm
    change_list_template = 'hpe_admin/problem_change_list.html'
    
    def get_form(self, request, obj=None, **kwargs):
        # Bypass ProblemAdmin.get_form
        return super(ProblemAdmin, self).get_form(request, obj, **kwargs)
    
    fieldsets = (
        (None, {'fields': ('code', 'name', 'authors', 'testers')}),
        (_('Resources'), {'fields': ('time_limit', 'memory_limit', 'points', 'partial')}),
        (_('Languages'), {'fields': ('allowed_languages',)}),
    )
    # Note: Bulk Upload button will be added via template

class HPEMCQQuestionAdmin(MCQQuestionAdmin):
    form = HPEMCQForm
    change_list_template = 'hpe_admin/mcq_change_list.html'
    
    def get_form(self, request, obj=None, **kwargs):
        # Bypass MCQQuestionAdmin.get_form
        return super(MCQQuestionAdmin, self).get_form(request, obj, **kwargs)
    
    fieldsets = (
        (None, {'fields': ('code', 'name', 'authors')}), # Removed 'testers' as it doesn't exist
        (_('Details'), {'fields': ('points', 'explanation')}),
    )
    # Note: Bulk Upload button will be added via template


# Register models
hpe_admin_site.register(Problem, HPEProblemAdmin)
hpe_admin_site.register(MCQQuestion, HPEMCQQuestionAdmin)
hpe_admin_site.register(Contest, HPEContestAdmin)
