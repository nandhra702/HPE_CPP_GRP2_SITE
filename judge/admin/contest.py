from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q, TextField
from django.forms import ModelForm, ModelMultipleChoiceField
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.decorators.http import require_POST
from reversion.admin import VersionAdmin
from judge.models import Class, Contest, ContestProblem, ContestSubmission, Profile, Rating, Submission, ContestMCQ, Problem, MCQQuestion
from judge.ratings import rate_contest
from judge.utils.views import NoBatchDeleteMixin
from judge.widgets import AdminAceWidget, AdminHeavySelect2MultipleWidget, AdminHeavySelect2Widget, \
    AdminMartorWidget, AdminSelect2MultipleWidget, AdminSelect2Widget
import csv
import json
from django.core.mail import send_mail
from django.contrib.auth.models import User
from judge.models import Profile
from django import forms
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings
from django.utils.crypto import get_random_string


class AdminHeavySelect2Widget(AdminHeavySelect2Widget):
    @property
    def is_hidden(self):
        return False


class DashboardButtonWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        return format_html(
            '<div style="margin: 10px 0;">'
            '<button type="button" class="button" onclick="openDashboard()" style="padding: 10px 20px; font-size: 14px; background-color: #2980B9; color: white; border: none; border-radius: 5px; cursor: pointer; transition: background-color 0.3s; display: inline-flex; justify-content: center; align-items: center; text-align: center; line-height: normal; width: auto;">Open Problems Dashboard</button>'
            '</div>'
            '<script>'
            'function openDashboard() {{'
            '   window.open("/judge-admin/contest/dashboard/", "ContestDashboard", "width=1200,height=800,scrollbars=yes,resizable=yes");'
            '}}'
            'window.updateContestSelections = function(problems, mcqs, randomization) {{'
            '   document.getElementById("id_contest_problems_json").value = JSON.stringify(problems);'
            '   document.getElementById("id_contest_mcqs_json").value = JSON.stringify(mcqs);'
            '   document.getElementById("id_contest_randomization_json").value = JSON.stringify(randomization);'
            '   alert("Selections updated! Click Save to persist.");'
            '}};'
            'window.getContestSelections = function() {{'
            '   const p = document.getElementById("id_contest_problems_json").value;'
            '   const m = document.getElementById("id_contest_mcqs_json").value;'
            '   const r = document.getElementById("id_contest_randomization_json").value;'
            '   return {{'
            '       problems: p ? JSON.parse(p) : [],'
            '       mcqs: m ? JSON.parse(m) : [],'
            '       randomization: r ? JSON.parse(r) : {{}}'
            '   }};'
            '}};'
            '</script>'
        )



class ContestTagForm(ModelForm):
    contests = ModelMultipleChoiceField(
        label=_('Included contests'),
        queryset=Contest.objects.all(),
        required=False,
        widget=AdminHeavySelect2MultipleWidget(data_view='contest_select2'))


class ContestTagAdmin(admin.ModelAdmin):
    fields = ('name', 'color', 'description', 'contests')
    list_display = ('name', 'color')
    actions_on_top = True
    actions_on_bottom = True
    form = ContestTagForm
    formfield_overrides = {
        TextField: {'widget': AdminMartorWidget},
    }

    def save_model(self, request, obj, form, change):
        super(ContestTagAdmin, self).save_model(request, obj, form, change)
        obj.contests.set(form.cleaned_data['contests'])

    def get_form(self, request, obj=None, **kwargs):
        form = super(ContestTagAdmin, self).get_form(request, obj, **kwargs)
        if obj is not None:
            form.base_fields['contests'].initial = obj.contests.all()
        return form


class ContestProblemInlineForm(ModelForm):
    class Meta:
        widgets = {'problem': AdminHeavySelect2Widget(data_view='problem_select2')}


class ContestProblemInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ContestProblem
    verbose_name = _('Problem')
    verbose_name_plural = _('Problems')
    fields = ('problem', 'points', 'partial', 'is_pretested', 'max_submissions', 'output_prefix_override', 'order',
              'rejudge_column')
    readonly_fields = ('rejudge_column',)
    form = ContestProblemInlineForm

    @admin.display(description='')
    def rejudge_column(self, obj):
        if obj.id is None:
            return ''
        return format_html('<a class="button rejudge-link action-link" href="{0}">{1}</a>',
                           reverse('admin:judge_contest_rejudge', args=(obj.contest.id, obj.id)), _('Rejudge'))


class ContestMCQInlineForm(ModelForm):
    class Meta:
        model = ContestMCQ
        fields = '__all__'


class ContestMCQInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ContestMCQ
    verbose_name = _('MCQ Question')
    verbose_name_plural = _('MCQ Questions')
    fields = ('mcq_question', 'points', 'order')
    form = ContestMCQInlineForm
    extra = 0


class ContestForm(ModelForm):
    emails_csv = forms.FileField(
        required=False,
        help_text=_("Upload a CSV or Excel file with email addresses to auto-create user accounts. Existing accounts will be skipped."),
    )
    private_contestants_csv = forms.FileField(
        required=False,
        label=_("Private Contestants CSV/Excel"),
        help_text=_("Upload CSV or Excel with email addresses to add as private contestants. Only existing users will be added."),
    )
    
    dashboard_button = forms.CharField(required=False, widget=DashboardButtonWidget, label="Problems Dashboard")
    contest_problems_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    contest_mcqs_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    contest_randomization_json = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(ContestForm, self).__init__(*args, **kwargs)
        if 'rate_exclude' in self.fields:
            if self.instance and self.instance.id:
                self.fields['rate_exclude'].queryset = \
                    Profile.objects.filter(contest_history__contest=self.instance).distinct()
            else:
                self.fields['rate_exclude'].queryset = Profile.objects.none()
        self.fields['banned_users'].widget.can_add_related = False
        self.fields['view_contest_scoreboard'].widget.can_add_related = False
        
        if self.instance and self.instance.pk:
            # Load existing selections
            p_data = []
            for cp in self.instance.contest_problems.select_related('problem', 'problem__group').order_by('order'):
                p_data.append({
                    'id': cp.problem_id,
                    'code': cp.problem.code,
                    'name': cp.problem.name,
                    'points': cp.points,
                    'partial': cp.partial,
                    'is_pretested': cp.is_pretested,
                    'max_submissions': cp.max_submissions,
                    'output_prefix_override': cp.output_prefix_override,
                    'order': cp.order,
                    'group': cp.problem.group.full_name if cp.problem.group else 'Uncategorized'
                })
            
            m_data = []
            for cm in self.instance.contest_mcqs.select_related('mcq_question', 'mcq_question__group').order_by('order'):
                m_data.append({
                    'id': cm.mcq_question_id,
                    'code': cm.mcq_question.code,
                    'name': cm.mcq_question.name,
                    'points': cm.points,
                    'order': cm.order,
                    'group': cm.mcq_question.group.full_name if cm.mcq_question.group else 'Uncategorized'
                })
                
            self.fields['contest_problems_json'].initial = json.dumps(p_data)
            self.fields['contest_mcqs_json'].initial = json.dumps(m_data)
            self.fields['contest_randomization_json'].initial = json.dumps(self.instance.randomization_config)

    def clean(self):
        cleaned_data = super(ContestForm, self).clean()
        cleaned_data['banned_users'].filter(current_contest__contest=self.instance).update(current_contest=None)

    class Meta:
        widgets = {
            'authors': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'curators': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'testers': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'spectators': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'private_contestants': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'organizations': AdminHeavySelect2MultipleWidget(data_view='organization_select2'),
            'classes': AdminHeavySelect2MultipleWidget(data_view='class_select2'),
            'join_organizations': AdminHeavySelect2MultipleWidget(data_view='organization_select2'),
            'tags': AdminSelect2MultipleWidget,
            'banned_users': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'view_contest_scoreboard': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'view_contest_submissions': AdminHeavySelect2MultipleWidget(data_view='profile_select2'),
            'description': AdminMartorWidget(attrs={'data-markdownfy-url': reverse_lazy('contest_preview')}),
        }


class ContestAdmin(NoBatchDeleteMixin, SortableAdminBase, VersionAdmin):
    fieldsets = (
        (None, {'fields': ('key', 'name', 'authors', 'curators', 'testers', 'tester_see_submissions',
                           'tester_see_scoreboard', 'spectators')}),
        (_('Problems'), {'fields': ('dashboard_button', 'contest_problems_json', 'contest_mcqs_json', 'contest_randomization_json')}),
        (_('Settings'), {'fields': ('is_visible', 'use_clarifications', 'hide_problem_tags', 'hide_problem_authors',
                                    'show_short_display', 'run_pretests_only', 'locked_after', 'scoreboard_visibility',
                                    'points_precision')}),
        (_('Scheduling'), {'fields': ('start_time', 'end_time', 'time_limit')}),
        (_('Details'), {'fields': ('description', 'og_image', 'logo_override_image', 'tags', 'summary')}),
        (_('Format'), {'fields': ('format_name', 'format_config', 'problem_label_script')}),
        (_('Rating'), {'fields': ('is_rated', 'rate_all', 'rating_floor', 'rating_ceiling',
                                  'performance_ceiling_override', 'rate_exclude')}),
        (_('Access'), {'fields': ('access_code', 'private_contestants', 'private_contestants_csv', 'organizations', 'classes',
                                  'join_organizations', 'view_contest_scoreboard', 'view_contest_submissions','emails_csv',)}),
        (_('Justice'), {'fields': ('banned_users',)}),
    )
    list_display = ('key', 'name', 'is_visible', 'is_rated', 'locked_after', 'start_time', 'end_time', 'time_limit',
                    'user_count')
    search_fields = ('key', 'name')
    inlines = []
    actions_on_top = True
    actions_on_bottom = True
    form = ContestForm
    change_list_template = 'admin/judge/contest/change_list.html'
    filter_horizontal = ['rate_exclude']
    date_hierarchy = 'start_time'

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Only rescored if we did not already do so in `save_model`
        if not self._rescored and any(formset.has_changed() for formset in formsets):
            self._rescore(form.cleaned_data['key'])
            
        # Process JSON data for Problems and MCQs
        if 'contest_problems_json' in form.cleaned_data and form.cleaned_data['contest_problems_json']:
            try:
                problems_data = json.loads(form.cleaned_data['contest_problems_json'])
                
                # Normalize input to list of dicts
                normalized_problems = []
                for item in problems_data:
                    if isinstance(item, int): # Old format (just IDs)
                        normalized_problems.append({'id': item})
                    else:
                        normalized_problems.append(item)
                
                current_problems = {cp.problem_id: cp for cp in form.instance.contest_problems.all()}
                new_ids = set(int(p['id']) for p in normalized_problems)
                
                # Delete removed
                form.instance.contest_problems.filter(problem_id__in=set(current_problems.keys()) - new_ids).delete()
                
                # Add new or update
                for i, p_item in enumerate(normalized_problems):
                    pid = int(p_item['id'])
                    
                    # Extract fields with defaults
                    points = p_item.get('points')
                    partial = p_item.get('partial', True)
                    is_pretested = p_item.get('is_pretested', False)
                    max_submissions = p_item.get('max_submissions')
                    output_prefix_override = p_item.get('output_prefix_override', 0)
                    
                    if pid in current_problems:
                        cp = current_problems[pid]
                        # Update fields
                        changed = False
                        if cp.order != i:
                            cp.order = i
                            changed = True
                        if points is not None and cp.points != points:
                            cp.points = points
                            changed = True
                        if cp.partial != partial:
                            cp.partial = partial
                            changed = True
                        if cp.is_pretested != is_pretested:
                            cp.is_pretested = is_pretested
                            changed = True
                        if cp.max_submissions != max_submissions:
                            cp.max_submissions = max_submissions
                            changed = True
                        if cp.output_prefix_override != output_prefix_override:
                            cp.output_prefix_override = output_prefix_override
                            changed = True
                            
                        if changed:
                            cp.save()
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
            except Exception as e:
                pass # Log error?

        if 'contest_mcqs_json' in form.cleaned_data and form.cleaned_data['contest_mcqs_json']:
            try:
                mcq_data = json.loads(form.cleaned_data['contest_mcqs_json'])
                
                normalized_mcqs = []
                for item in mcq_data:
                    if isinstance(item, int):
                        normalized_mcqs.append({'id': item})
                    else:
                        normalized_mcqs.append(item)

                current_mcqs = {cm.mcq_question_id: cm for cm in form.instance.contest_mcqs.all()}
                new_ids = set(int(m['id']) for m in normalized_mcqs)
                
                form.instance.contest_mcqs.filter(mcq_question_id__in=set(current_mcqs.keys()) - new_ids).delete()
                
                for i, m_item in enumerate(normalized_mcqs):
                    mid = int(m_item['id'])
                    points = m_item.get('points')

                    if mid in current_mcqs:
                        cm = current_mcqs[mid]
                        changed = False
                        if cm.order != i:
                            cm.order = i
                            changed = True
                        if points is not None and cm.points != points:
                            cm.points = points
                            changed = True
                        
                        if changed:
                            cm.save()
                    else:
                        mcq = MCQQuestion.objects.get(id=mid)
                        ContestMCQ.objects.create(
                            contest=form.instance,
                            mcq_question=mcq,
                            points=points if points is not None else mcq.points,
                            order=i
                        )
            except Exception as e:
                pass

        if 'contest_randomization_json' in form.cleaned_data and form.cleaned_data['contest_randomization_json']:
            try:
                randomization_data = json.loads(form.cleaned_data['contest_randomization_json'])
                form.instance.randomization_config = randomization_data
                # Update randomize boolean based on config
                form.instance.randomize = randomization_data.get('regular_enabled', False) or \
                                          randomization_data.get('mcq_enabled', False) or \
                                          randomization_data.get('enabled', False)
                form.instance.save(update_fields=['randomization_config', 'randomize'])
            except Exception as e:
                pass

    def has_change_permission(self, request, obj=None):
        if not request.user.has_perm('judge.edit_own_contest'):
            return False
        if obj is None:
            return True
        return obj.is_editable_by(request.user)

    def _rescore(self, contest_key):
        from judge.tasks import rescore_contest
        transaction.on_commit(rescore_contest.s(contest_key).delay)

    @admin.display(description=_('Mark contests as visible'))
    def make_visible(self, request, queryset):
        if not request.user.has_perm('judge.change_contest_visibility'):
            queryset = queryset.filter(Q(is_private=True) | Q(is_organization_private=True))
        count = queryset.update(is_visible=True)
        self.message_user(request, ngettext('%d contest successfully marked as visible.',
                                            '%d contests successfully marked as visible.',
                                            count) % count)

    @admin.display(description=_('Mark contests as hidden'))
    def make_hidden(self, request, queryset):
        if not request.user.has_perm('judge.change_contest_visibility'):
            queryset = queryset.filter(Q(is_private=True) | Q(is_organization_private=True))
        count = queryset.update(is_visible=False)
        self.message_user(request, ngettext('%d contest successfully marked as hidden.',
                                            '%d contests successfully marked as hidden.',
                                            count) % count)

    @admin.display(description=_('Lock contest submissions'))
    def set_locked(self, request, queryset):
        for row in queryset:
            self.set_locked_after(row, timezone.now())
        count = queryset.count()
        self.message_user(request, ngettext('%d contest successfully locked.',
                                            '%d contests successfully locked.',
                                            count) % count)

    @admin.display(description=_('Unlock contest submissions'))
    def set_unlocked(self, request, queryset):
        for row in queryset:
            self.set_locked_after(row, None)
        count = queryset.count()
        self.message_user(request, ngettext('%d contest successfully unlocked.',
                                            '%d contests successfully unlocked.',
                                            count) % count)

    def set_locked_after(self, contest, locked_after):
        with transaction.atomic():
            contest.locked_after = locked_after
            contest.save()
            Submission.objects.filter(contest_object=contest,
                                      contest__participation__virtual=0).update(locked_after=locked_after)

    def get_urls(self):
        return [
            path('rate/all/', self.rate_all_view, name='judge_contest_rate_all'),
            path('<int:id>/rate/', self.rate_view, name='judge_contest_rate'),
            path('<int:contest_id>/judge/<int:problem_id>/', self.rejudge_view, name='judge_contest_rejudge'),
            path('<int:contest_id>/generate-accounts/', self.generate_accounts_view, name='judge_contest_generate_accounts'),
            path('generate-accounts/', self.generate_accounts_view, name='judge_contest_generate_accounts_new'),
            path('<int:contest_id>/add-private-contestants/', self.add_private_contestants_view, name='judge_contest_add_private_contestants'),
            path('add-private-contestants/', self.add_private_contestants_view, name='judge_contest_add_private_contestants_new'),
        ] + super(ContestAdmin, self).get_urls()

    @method_decorator(require_POST)
    def rejudge_view(self, request, contest_id, problem_id):
        contest = get_object_or_404(Contest, id=contest_id)
        if not self.has_change_permission(request, contest):
            raise PermissionDenied()
        queryset = ContestSubmission.objects.filter(problem_id=problem_id).select_related('submission')
        for model in queryset:
            model.submission.judge(rejudge=True, rejudge_user=request.user)

        self.message_user(request, ngettext('%d submission was successfully scheduled for rejudging.',
                                            '%d submissions were successfully scheduled for rejudging.',
                                            len(queryset)) % len(queryset))
        return HttpResponseRedirect(reverse('admin:judge_contest_change', args=(contest_id,)))

    @method_decorator(require_POST)
    def rate_all_view(self, request):
        if not request.user.has_perm('judge.contest_rating'):
            raise PermissionDenied()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('TRUNCATE TABLE `%s`' % Rating._meta.db_table)
            Profile.objects.update(rating=None)
            for contest in Contest.objects.filter(is_rated=True, end_time__lte=timezone.now()).order_by('end_time'):
                rate_contest(contest)
        return HttpResponseRedirect(reverse('admin:judge_contest_changelist'))

    @method_decorator(require_POST)
    def rate_view(self, request, id):
        if not request.user.has_perm('judge.contest_rating'):
            raise PermissionDenied()
        contest = get_object_or_404(Contest, id=id)
        if not contest.is_rated or not contest.ended:
            raise Http404()
        with transaction.atomic():
            contest.rate()
        return HttpResponseRedirect(request.headers.get('referer', reverse('admin:judge_contest_changelist')))

    @method_decorator(require_POST)
    def generate_accounts_view(self, request, contest_id=None):
        """Handle CSV/Excel file upload and generate user accounts"""
        from django.http import JsonResponse
        
        if not request.user.has_perm('judge.change_contest'):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        csv_file = request.FILES.get('emails_csv')
        if not csv_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        try:
            # Try to import pandas for Excel support
            try:
                import pandas as pd
                HAS_PANDAS = True
            except ImportError:
                HAS_PANDAS = False
            
            emails = []
            file_name = csv_file.name.lower()
            
            # Handle CSV files
            if file_name.endswith('.csv'):
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.reader(decoded_file)
                next(reader, None)  # skip header if present
                
                for row in reader:
                    if row and row[0].strip():
                        emails.append(row[0].strip())
            
            # Handle Excel files
            elif file_name.endswith(('.xlsx', '.xls')):
                if not HAS_PANDAS:
                    return JsonResponse({
                        'error': 'Excel file support requires pandas. Please install pandas and openpyxl.'
                    }, status=400)
                
                df = pd.read_excel(csv_file)
                # Try to find email column (case-insensitive)
                email_col = None
                for col in df.columns:
                    if 'email' in str(col).lower():
                        email_col = col
                        break
                
                if email_col is None:
                    # If no email column found, use first column
                    email_col = df.columns[0]
                
                for email in df[email_col].dropna():
                    if str(email).strip():
                        emails.append(str(email).strip())
            
            else:
                return JsonResponse({
                    'error': 'Unsupported file format. Please upload CSV or Excel files.'
                }, status=400)
            
            # Process each email
            created_count = 0
            skipped_count = 0
            failed_emails = []
            
            for email in emails:
                # Check if user with this email already exists
                if User.objects.filter(email=email).exists():
                    skipped_count += 1
                    continue
                
                # Generate unique username from email
                base_username = email.split('@')[0][:20]  # Limit to 20 chars
                username = base_username
                counter = 1
                
                # Ensure username is unique
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                # Generate random password
                password = get_random_string(12)
                
                try:
                    # Create new user
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                    
                    # Create associated profile
                    Profile.objects.get_or_create(user=user)
                    
                    # Send welcome email with credentials
                    email_subject = 'Your Account Credentials - Please Change Password'
                    email_message = f"""Hello,

An account has been created for you.

Username: {username}
Temporary Password: {password}

IMPORTANT: Please log in and change your password immediately for security purposes.

Login at: {settings.SITE_FULL_URL if hasattr(settings, 'SITE_FULL_URL') else 'your-site-url'}

If you did not request this account, please contact support.

Best regards,
{settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Admin Team'}"""
                    
                    try:
                        send_mail(
                            subject=email_subject,
                            message=email_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        created_count += 1
                    except Exception as e:
                        failed_emails.append((email, str(e)))
                        created_count += 1  # Still count as created even if email failed
                
                except Exception as e:
                    failed_emails.append((email, str(e)))
            
            # Build response message
            message_parts = []
            if created_count > 0:
                message_parts.append(f"Successfully created {created_count} new account(s)")
            if skipped_count > 0:
                message_parts.append(f"Skipped {skipped_count} existing account(s)")
            if failed_emails:
                message_parts.append(f"Failed to process {len(failed_emails)} email(s)")
            
            details = " | ".join(message_parts) if message_parts else "No accounts processed"
            
            return JsonResponse({
                'message': f'Account generation complete!',
                'details': details,
                'created': created_count,
                'skipped': skipped_count,
                'failed': len(failed_emails)
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error processing file: {str(e)}'
            }, status=500)

    @method_decorator(require_POST)
    def add_private_contestants_view(self, request, contest_id=None):
        """Handle CSV/Excel file upload and add users to private_contestants"""
        from django.http import JsonResponse
        
        if not request.user.has_perm('judge.change_contest'):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get the contest if it exists (None for unsaved contests)
        contest = None
        if contest_id:
            contest = get_object_or_404(Contest, id=contest_id)
        
        csv_file = request.FILES.get('private_contestants_csv')
        if not csv_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        try:
            # Try to import pandas for Excel support
            try:
                import pandas as pd
                HAS_PANDAS = True
            except ImportError:
                HAS_PANDAS = False
            
            emails = []
            file_name = csv_file.name.lower()
            
            # Handle CSV files
            if file_name.endswith('.csv'):
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.reader(decoded_file)
                next(reader, None)  # skip header if present
                
                for row in reader:
                    if row and row[0].strip():
                        emails.append(row[0].strip())
            
            # Handle Excel files
            elif file_name.endswith(('.xlsx', '.xls')):
                if not HAS_PANDAS:
                    return JsonResponse({
                        'error': 'Excel file support requires pandas. Please install pandas and openpyxl.'
                    }, status=400)
                
                df = pd.read_excel(csv_file)
                # Try to find email column (case-insensitive)
                email_col = None
                for col in df.columns:
                    if 'email' in str(col).lower():
                        email_col = col
                        break
                
                if email_col is None:
                    # If no email column found, use first column
                    email_col = df.columns[0]
                
                for email in df[email_col].dropna():
                    if str(email).strip():
                        emails.append(str(email).strip())
            
            else:
                return JsonResponse({
                    'error': 'Unsupported file format. Please upload CSV or Excel files.'
                }, status=400)
            
            if not emails:
                return JsonResponse({
                    'error': 'No email addresses found in file.'
                }, status=400)
            
            # Process each email
            added_count = 0
            already_added_count = 0
            not_found_count = 0
            not_found_emails = []
            profile_data = []  # Store profile data (id, username) for unsaved contests
            
            for email in emails:
                try:
                    # Lookup user by email
                    user = User.objects.get(email=email)
                    
                    # Check if user has a profile
                    if not hasattr(user, 'profile'):
                        not_found_count += 1
                        not_found_emails.append(email)
                        continue
                    
                    profile = user.profile
                    
                    if contest:
                        # For saved contests: add directly to ManyToMany field
                        # Check if already added
                        if contest.private_contestants.filter(id=profile.id).exists():
                            already_added_count += 1
                        else:
                            # Add to private contestants
                            contest.private_contestants.add(profile)
                            added_count += 1
                    else:
                        # For unsaved contests: return profile data (id and display name)
                        profile_data.append({
                            'id': profile.id,
                            'text': profile.user.username  # This is what select2 needs
                        })
                        added_count += 1
                        
                except User.DoesNotExist:
                    not_found_count += 1
                    not_found_emails.append(email)
            
            # Auto-set is_private flag if contestants were added (only for saved contests)
            if contest and added_count > 0 and not contest.is_private:
                contest.is_private = True
                contest.save()
            
            # Build response message
            if contest:
                message = f"Successfully added {added_count} user(s) to private contestants."
            else:
                message = f"Found {added_count} user(s) to add as private contestants. Save the contest to apply changes."
            
            if already_added_count > 0:
                message += f" Skipped {already_added_count} already added."
            if not_found_count > 0:
                message += f" Could not find {not_found_count} user(s) in the system."
            
            response_data = {
                'message': message,
                'added': added_count,
                'already_added': already_added_count,
                'not_found': not_found_count,
            }
            
            # Include profile data for unsaved contests
            if not contest and profile_data:
                response_data['profile_data'] = profile_data
            
            if not_found_emails and len(not_found_emails) <= 10:
                response_data['not_found_emails'] = not_found_emails
            elif not_found_emails:
                response_data['details'] = f"First 10 not found: {', '.join(not_found_emails[:10])}"
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error processing file: {str(e)}'
            }, status=500)

    def get_form(self, request, obj=None, **kwargs):
        form = super(ContestAdmin, self).get_form(request, obj, **kwargs)
        if 'problem_label_script' in form.base_fields:
            # form.base_fields['problem_label_script'] does not exist when the user has only view permission
            # on the model.
            form.base_fields['problem_label_script'].widget = AdminAceWidget(
                mode='lua', theme=request.profile.resolved_ace_theme,
            )

        perms = ('edit_own_contest', 'edit_all_contest')
        form.base_fields['curators'].queryset = Profile.objects.filter(
            Q(user__is_superuser=True) |
            Q(user__groups__permissions__codename__in=perms) |
            Q(user__user_permissions__codename__in=perms),
        ).distinct()
        form.base_fields['classes'].queryset = Class.get_visible_classes(request.user)
        return form
    def save_model(self, request, obj, form, change):
        # `private_contestants` and `organizations` will not appear in `cleaned_data` if user cannot edit it
        if form.changed_data:
            if 'private_contestants' in form.changed_data:
                obj.is_private = bool(form.cleaned_data['private_contestants'])
            if 'organizations' in form.changed_data or 'classes' in form.changed_data:
                obj.is_organization_private = bool(form.cleaned_data['organizations'] or form.cleaned_data['classes'])
            if 'join_organizations' in form.cleaned_data:
                obj.limit_join_organizations = bool(form.cleaned_data['join_organizations'])

        # `is_visible` will not appear in `cleaned_data` if user cannot edit it
        if form.cleaned_data.get('is_visible') and not request.user.has_perm('judge.change_contest_visibility'):
            if not obj.is_private and not obj.is_organization_private:
                raise PermissionDenied
            if not request.user.has_perm('judge.create_private_contest'):
                raise PermissionDenied

        super().save_model(request, obj, form, change)
        # We need this flag because `save_related` deals with the inlines, but does not know if we have already rescored
        self._rescored = False
        if form.changed_data and any(f in form.changed_data for f in ('format_config', 'format_name')):
            self._rescore(obj.key)
            self._rescored = True

        if form.changed_data and 'locked_after' in form.changed_data:
            self.set_locked_after(obj, form.cleaned_data['locked_after'])




class ContestParticipationForm(ModelForm):
    class Meta:
        widgets = {
            'contest': AdminSelect2Widget(),
            'user': AdminHeavySelect2Widget(data_view='profile_select2'),
        }


class ContestParticipationAdmin(admin.ModelAdmin):
    fields = ('contest', 'user', 'real_start', 'virtual', 'is_disqualified', 'has_exited')
    list_display = ('contest', 'username', 'show_virtual', 'real_start', 'score', 'cumtime', 'tiebreaker', 'has_exited')
    actions = ['recalculate_results']
    actions_on_bottom = actions_on_top = True
    search_fields = ('contest__key', 'contest__name', 'user__user__username')
    form = ContestParticipationForm
    date_hierarchy = 'real_start'

    def get_queryset(self, request):
        return super(ContestParticipationAdmin, self).get_queryset(request).only(
            'contest__name', 'contest__format_name', 'contest__format_config',
            'user__user__username', 'real_start', 'score', 'cumtime', 'tiebreaker', 'virtual',
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.changed_data and 'is_disqualified' in form.changed_data:
            obj.set_disqualified(obj.is_disqualified)

    @admin.display(description=_('Recalculate results'))
    def recalculate_results(self, request, queryset):
        count = 0
        for participation in queryset:
            participation.recompute_results()
            count += 1
        self.message_user(request, ngettext('%d participation recalculated.',
                                            '%d participations recalculated.',
                                            count) % count)

    @admin.display(description=_('username'), ordering='user__user__username')
    def username(self, obj):
        return obj.user.username

    @admin.display(description=_('virtual'), ordering='virtual')
    def show_virtual(self, obj):
        return obj.virtual or '-'
