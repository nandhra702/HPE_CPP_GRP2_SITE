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
from .forms import ContestParticipantUploadForm, HPEContestForm, HPEProblemForm, HPEMCQForm, HPEProblemBulkUploadForm

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
    change_form_template = 'hpe_admin/problem_change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
             path('bulk-upload/', self.bulk_upload_view, name='hpe_problem_bulk_upload'),
        ]
        return custom_urls + urls

    def bulk_upload_view(self, request):
        if request.method == 'POST':
            form = HPEProblemBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    uploaded_file = request.FILES['csv_file']
                    file_name = uploaded_file.name.lower()
                    
                    import csv
                    import io
                    import zipfile
                    import yaml
                    from django.core.files.base import ContentFile
                    from django.utils.text import slugify
                    from judge.models import ProblemData
                    
                    rows = []
                    
                    # Handle Excel files (.xlsx)
                    if file_name.endswith('.xlsx'):
                        from openpyxl import load_workbook
                        wb = load_workbook(filename=io.BytesIO(uploaded_file.read()))
                        ws = wb.active
                        for row in ws.iter_rows(values_only=True):
                            # Convert None to empty string and ensure all are strings
                            rows.append([str(cell) if cell is not None else '' for cell in row])
                    else:
                        # Handle CSV files
                        decoded_file = uploaded_file.read().decode('utf-8').splitlines()
                        reader = csv.reader(decoded_file)
                        rows = list(reader)
                    
                    # Expected format: Name, Body, Constraints, TL, ML, Difficulty, In1, Out1, In2, Out2...
                    
                    # Map difficulty names to group IDs
                    difficulty_map = {
                        'easy': 2,
                        'medium': 3,
                        'hard': 4,
                    }
                    
                    count = 0
                    for row in rows:
                        if len(row) < 6: continue # Minimum fields (including difficulty)
                        
                        name = row[0].strip()
                        if not name: continue  # Skip empty rows or header rows
                        
                        body = row[1]
                        constraints = row[2]
                        
                        # Handle Null/empty time limit - default to 60 seconds (max reasonable)
                        tl_value = row[3].strip().lower() if row[3] else ''
                        if tl_value in ('null', 'none', '') or not tl_value:
                            time_limit = 60.0  # Default max time limit
                        else:
                            try:
                                time_limit = float(row[3])
                            except:
                                time_limit = 60.0
                        
                        # Handle Null/empty memory limit - default to 512MB (524288 KB)
                        ml_value = row[4].strip().lower() if row[4] else ''
                        if ml_value in ('null', 'none', '') or not ml_value:
                            memory_limit = 524288  # 512MB default
                        else:
                            try:
                                memory_limit = int(row[4])
                            except:
                                memory_limit = 524288
                        
                        # Handle Difficulty level - REQUIRED (easy/medium/hard)
                        # Get the difficulty value safely
                        raw_difficulty = row[5] if len(row) > 5 and row[5] else ''
                        difficulty_value = raw_difficulty.strip().lower()
                        
                        if difficulty_value not in difficulty_map:
                            messages.error(request, f"Row '{name}': Invalid difficulty '{raw_difficulty}'. Must be easy, medium, or hard (case insensitive).")
                            continue  # Skip this row
                        group_id = difficulty_map[difficulty_value]
                        
                        # Generate unique problem code from name
                        base_code = slugify(name)[:20] or "prob"
                        code = base_code
                        suffix = 1
                        while Problem.objects.filter(code=code).exists():
                            code = f"{base_code}{suffix}"
                            suffix += 1
                        
                        # Parse test cases first to build Examples (now starting from index 6)
                        test_cases_data = row[6:]
                        examples_md = ""
                        example_num = 1
                        
                        # Build Examples section from test case pairs
                        for i in range(0, len(test_cases_data), 2):
                            if i + 1 >= len(test_cases_data): break
                            
                            in_data = test_cases_data[i]
                            out_data = test_cases_data[i+1]
                            
                            # Only show first 2 examples in description (visible to users)
                            if example_num <= 2:
                                examples_md += f"\n## Example {example_num}\n"
                                examples_md += f"**Input:**\n```\n{in_data}\n```\n\n"
                                examples_md += f"**Output:**\n```\n{out_data}\n```\n"
                            
                            example_num += 1
                        
                        # Build the full markdown description
                        description = body
                        
                        if examples_md:
                            description += f"\n{examples_md}"
                        
                        if constraints and constraints.lower() != 'none':
                            description += f"\n## Constraints\n{constraints}\n"
                            
                        # Create Problem with difficulty group
                        problem = Problem.objects.create(
                            code=code,
                            name=name,
                            description=description,
                            time_limit=time_limit,
                            memory_limit=memory_limit,
                            points=0,  # Default points (can be adjusted later)
                            is_public=False,
                            is_manually_managed=True,
                            group_id=group_id  # Use mapped difficulty group
                        )
                        
                        # M2M
                        if form.cleaned_data['creators']:
                            problem.authors.set(form.cleaned_data['creators'])
                        if form.cleaned_data['testers']:
                            problem.testers.set(form.cleaned_data['testers'])
                        if form.cleaned_data['allowed_languages']:
                            problem.allowed_languages.set(form.cleaned_data['allowed_languages'])
                            
                        # Test Cases - Create folder structure in site/problems/{code}/
                        if test_cases_data:
                            import os
                            from django.conf import settings
                            
                            # Get the problems directory path
                            problems_dir = os.path.join(settings.BASE_DIR, 'problems')
                            problem_dir = os.path.join(problems_dir, code)
                            
                            # Create the problem directory
                            os.makedirs(problem_dir, exist_ok=True)
                            
                            # Build init.yml content
                            init_yml_content = {
                                'name': name,
                                'code': code,
                                'type': 'standard',
                                'validator': 'token',
                                'limits': {
                                    'time': time_limit,
                                    'memory': memory_limit
                                },
                                'archive': 'testcases.zip',
                                'cases': []
                            }
                            
                            # Create individual test case files and add to zip
                            zip_buffer = io.BytesIO()
                            
                            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                                case_idx = 1
                                for i in range(0, len(test_cases_data), 2):
                                    if i + 1 >= len(test_cases_data): break
                                    
                                    in_data = test_cases_data[i]
                                    out_data = test_cases_data[i+1]
                                    
                                    in_name = f"{case_idx}.in"
                                    out_name = f"{case_idx}.out"
                                    
                                    # Write individual files to folder
                                    with open(os.path.join(problem_dir, in_name), 'w') as f:
                                        f.write(in_data)
                                    with open(os.path.join(problem_dir, out_name), 'w') as f:
                                        f.write(out_data)
                                    
                                    # Add to zip
                                    zf.writestr(in_name, in_data)
                                    zf.writestr(out_name, out_data)
                                    
                                    init_yml_content['cases'].append({
                                        'in': in_name,
                                        'out': out_name
                                    })
                                    case_idx += 1
                            
                            if init_yml_content['cases']:
                                # Write init.yml to folder
                                with open(os.path.join(problem_dir, 'init.yml'), 'w') as f:
                                    yaml.dump(init_yml_content, f, default_flow_style=False)
                                
                                # Write testcases.zip to folder
                                with open(os.path.join(problem_dir, 'testcases.zip'), 'wb') as f:
                                    f.write(zip_buffer.getvalue())
                        
                        count += 1
                    
                    messages.success(request, f"Successfully uploaded {count} problems.")
                    return redirect('hpe_admin:judge_problem_changelist')
                    
                except Exception as e:
                    messages.error(request, f"Error processing file: {e}")
        else:
            form = HPEProblemBulkUploadForm()
            
        return render(request, 'hpe_admin/bulk_problem_upload.html', {
            'form': form,
            'title': _('Bulk Upload Problems')
        })
    
    def get_form(self, request, obj=None, **kwargs):
        # Bypass ProblemAdmin.get_form
        return super(ProblemAdmin, self).get_form(request, obj, **kwargs)
    
    fieldsets = (
        (None, {'fields': ('code', 'name', 'authors', 'testers')}),
        (_('Problem Body'), {'fields': ('description',)}),
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
