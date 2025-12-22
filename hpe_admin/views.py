from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.views.generic import DetailView, TemplateView
from django.views import View
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.http import Http404

from judge.models import Contest, ContestParticipation
from judge.debug import get_hpe_contest_backend_connect, get_allow_copy_paste
from judge.views.contests import _handle_contest_randomization


class HPEContestLandingView(View):
    """Public landing page for HPE contests with inline login."""
    template_name = 'hpe_admin/contest_landing.html'
    
    def get_contest(self, contest_key):
        return get_object_or_404(Contest, key=contest_key)
    
    def get_context_data(self, contest, request=None):
        # Calculate duration
        if contest.time_limit:
            total_seconds = int(contest.time_limit.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            if hours > 0:
                duration_display = f"{hours} hr {minutes} mins" if minutes else f"{hours} hr"
            else:
                duration_display = f"{minutes} mins"
        else:
            # Use contest window if no time limit
            duration = contest.end_time - contest.start_time
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60
            if hours > 0:
                duration_display = f"{hours} hr {minutes} mins" if minutes else f"{hours} hr"
            else:
                duration_display = f"{minutes} mins"
        
        # Check if user has a participation with randomized selection
        selected_problem_ids = None
        selected_mcq_ids = None
        if request and request.user.is_authenticated:
            participation = ContestParticipation.objects.filter(
                contest=contest,
                user=request.user.profile,
                virtual=ContestParticipation.LIVE
            ).first()
            if participation and participation.format_data:
                selected_problem_ids = participation.format_data.get('selected_problems')
                selected_mcq_ids = participation.format_data.get('selected_mcqs')
        
        # Get problems with details (filtered by randomization if applicable)
        problems = []
        for cp in contest.contest_problems.select_related('problem').order_by('order'):
            # Filter by selected_problems if randomization applied
            if selected_problem_ids is not None and cp.problem_id not in selected_problem_ids:
                continue
            problems.append({
                'label': f"Problem {len(problems) + 1}",
                'name': cp.problem.name,
                'code': cp.problem.code,
                'points': cp.points,
                'type': 'coding'
            })
        
        # Get MCQs with details (filtered by randomization if applicable)
        mcqs = []
        for cm in contest.contest_mcqs.select_related('mcq_question').order_by('order'):
            # Filter by selected_mcqs if randomization applied
            if selected_mcq_ids is not None and cm.mcq_question_id not in selected_mcq_ids:
                continue
            mcqs.append({
                'label': f"MCQ {len(mcqs) + 1}",
                'name': cm.mcq_question.code,
                'id': cm.mcq_question.id,
                'points': cm.points,
                'type': 'mcq'
            })
        
        # Combine all questions
        all_questions = problems + mcqs
        total_points = sum(q['points'] for q in all_questions)
        
        # Calculate expected counts from randomization config (for landing page display)
        # This shows users what they'll get AFTER they join
        expected_problem_count = len(problems)
        expected_mcq_count = len(mcqs)
        
        if contest.randomize and contest.randomization_config:
            config = contest.randomization_config
            
            # Calculate expected problem count from config
            if config.get('regular_enabled'):
                expected_problem_count = 0
                # Sum up the counts from config
                config_values = config.get('config', {})
                for key, count in config_values.items():
                    if not key.startswith('MCQ:'):  # Regular problems
                        expected_problem_count += count
            
            # Calculate expected MCQ count from config
            if config.get('mcq_enabled'):
                expected_mcq_count = 0
                config_values = config.get('config', {})
                for key, count in config_values.items():
                    if key.startswith('MCQ:'):  # MCQ problems
                        expected_mcq_count += count
        
        expected_total = expected_problem_count + expected_mcq_count
        
        return {
            'contest': contest,
            'duration_display': duration_display,
            'total_questions': expected_total,  # Use expected count for landing page
            'problem_count': expected_problem_count,
            'mcq_count': expected_mcq_count,
            'questions': all_questions,
            'total_points': total_points,
            'hpe_backend_connect': get_hpe_contest_backend_connect(),
            'allow_copy_paste': get_allow_copy_paste(),
        }

    
    def check_permission(self, user, contest):
        """Check if authenticated user can access the contest."""
        if user.has_perm('judge.edit_all_contest'):
            return True
        if user.profile in contest.authors.all():
            return True
        if user.profile in contest.curators.all():
            return True
        if contest.private_contestants.filter(id=user.profile.id).exists():
            return True
        return False
    
    def get(self, request, contest_key):
        contest = self.get_contest(contest_key)
        
        # If user is already authenticated, check permission and redirect
        if request.user.is_authenticated:
            if self.check_permission(request.user, contest):
                # Stay on page for multi-step flow instead of redirecting
                context = self.get_context_data(contest, request)
                context['logged_in'] = True
                return render(request, self.template_name, context)
            else:
                # Show landing page with permission denied error
                context = self.get_context_data(contest, request)
                context['error'] = "You do not have permission to access this contest."
                return render(request, self.template_name, context)
        
        context = self.get_context_data(contest, request)
        return render(request, self.template_name, context)
    
    def post(self, request, contest_key):
        from django.http import JsonResponse
        
        contest = self.get_contest(contest_key)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Please enter both username and password.'})
            context = self.get_context_data(contest, request)
            context['form_errors'] = ['Please enter both username and password.']
            return render(request, self.template_name, context)
        
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Invalid username or password.'})
            context = self.get_context_data(contest, request)
            context['form_errors'] = ['Invalid username or password.']
            return render(request, self.template_name, context)
        
        # Check contest permission before logging in
        if not self.check_permission(user, contest):
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'You do not have permission to access this contest.'})
            context = self.get_context_data(contest, request)
            context['error'] = "You do not have permission to access this contest."
            return render(request, self.template_name, context)
        
        # Login the user
        login(request, user)
        
        if is_ajax:
            return JsonResponse({'success': True})
        
        # For non-AJAX, redirect to the same page (now logged in)
        return redirect('hpe_contest_landing', contest_key=contest.key)


class HPEContestLoginView(auth_views.LoginView):
    template_name = 'hpe_admin/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # Redirect to a default contest or dashboard if accessed directly, 
        # but typically the user clicks a link to a specific contest.
        # Use existing 'next' param priority.
        url = self.get_redirect_url()
        if url:
            return url
        # Fallback to main site home if no next URL is provided to prevent redirection loop
        return '/'


class HPEContestLogoutView(View):
    """Seamless logout that redirects back to contest landing without showing DMOJ logout page."""
    
    def get(self, request, contest_key):
        logout(request)
        return redirect('hpe_contest_landing', contest_key=contest_key)


class HPEContestAccessMixin(LoginRequiredMixin):
    login_url = reverse_lazy('hpe_contest_login')

    def get_contest(self):
        key = self.kwargs.get('contest_key')
        return get_object_or_404(Contest, key=key)
        
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        self.contest = self.get_contest()
        
        # Access Check Logic
        if request.user.has_perm('judge.edit_all_contest') or \
           request.user.profile in self.contest.authors.all() or \
           request.user.profile in self.contest.curators.all():
            return super().dispatch(request, *args, **kwargs)
            
        if self.contest.private_contestants.filter(id=request.user.profile.id).exists():
            return super().dispatch(request, *args, **kwargs)
            
        return render(request, 'hpe_admin/access_denied.html', {'contest': self.contest}, status=403)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contest'] = self.contest
        return context

class HPEContestView(HPEContestAccessMixin, DetailView):
    # This is the old portal entry point
    # We redirect to the new landing page flow
    def get(self, request, *args, **kwargs):
        return redirect('hpe_contest_landing', contest_key=self.contest.key)




class HPEExamContentView(HPEContestAccessMixin, View):
    """Returns exam dashboard content as HTML fragment for SPA loading."""
    
    def get(self, request, *args, **kwargs):
        from django.template.loader import render_to_string
        
        # Build DMOJ data for proctoring
        dmoj_data = {
            'userId': request.user.id,
            'username': request.user.username,
            'contestName': self.contest.name,
            'contestKey': self.contest.key,
        }
        
        # Get filtered problems/MCQs based on randomization
        participation = ContestParticipation.objects.filter(
            contest=self.contest,
            user=request.user.profile,
            virtual=ContestParticipation.LIVE
        ).first()
        
        # Get problem/MCQ IDs from participation format_data (if randomization applied)
        selected_problem_ids = None
        selected_mcq_ids = None
        if participation and participation.format_data:
            selected_problem_ids = participation.format_data.get('selected_problems')
            selected_mcq_ids = participation.format_data.get('selected_mcqs')
        
        # Filter contest problems
        contest_problems = self.contest.contest_problems.select_related('problem').order_by('order')
        if selected_problem_ids is not None:
            contest_problems = contest_problems.filter(problem_id__in=selected_problem_ids)
        
        # Filter contest MCQs
        contest_mcqs = self.contest.contest_mcqs.select_related('mcq_question').order_by('order')
        if selected_mcq_ids is not None:
            contest_mcqs = contest_mcqs.filter(mcq_question_id__in=selected_mcq_ids)
        
        # Calculate the correct end time - use participation.end_time if available
        # This correctly handles time_limit for user's personal contest end time
        if participation:
            exam_end_time = participation.end_time.isoformat() if participation.end_time else self.contest.end_time.isoformat()
        else:
            exam_end_time = self.contest.end_time.isoformat()
        
        context = {
            'contest': self.contest,
            'dmoj_data': dmoj_data,
            'request': request,
            'hpe_backend_connect': get_hpe_contest_backend_connect(),
            'allow_copy_paste': get_allow_copy_paste(),
            'filtered_contest_problems': list(contest_problems),
            'filtered_contest_mcqs': list(contest_mcqs),
            'problem_codes': [cp.problem.code for cp in contest_problems],
            'exam_end_time': exam_end_time,  # Add participation-aware end time
        }
        
        html = render_to_string('hpe_admin/exam_content.html', context, request=request)
        return JsonResponse({
            'success': True,
            'html': html,
            'dmoj_data': dmoj_data,
            'exam_end_time': exam_end_time,  # Also return in JSON for JS to use
        })


from judge.models import Problem, ContestProblem, Language, Submission
from django.http import JsonResponse
from django.views import View
from django.utils.html import escape
from django.template.loader import render_to_string
import json

class HPEProblemContentAjaxView(HPEContestAccessMixin, View):
    """Returns problem details as JSON for the SPA editor."""
    
    def get_contest_problem(self):
        code = self.kwargs.get('problem_code')
        try:
            return ContestProblem.objects.select_related('problem').get(
                contest=self.contest, 
                problem__code=code
            )
        except ContestProblem.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        cp = self.get_contest_problem()
        if not cp:
            return JsonResponse({'error': 'Problem not found'}, status=404)
        
        problem = cp.problem
        
        # Get available languages for this problem
        languages = []
        for lang in problem.usable_languages.all():
            languages.append({
                'id': lang.id,
                'name': lang.name,
                'ace_mode': lang.ace,
                'template': lang.template or ''
            })
        
        # Render problem description HTML using DMOJ's markdown
        try:
            from judge.jinja2.markdown import markdown
            from django.conf import settings
            # Use the problem's markdown style and render to HTML
            math_engine = getattr(settings, 'MATH_ENGINE', None)
            description_html = str(markdown(
                problem.description or '', 
                problem.markdown_style, 
                math_engine=math_engine
            ))
        except Exception as e:
            # Fallback to basic escaped text
            description_html = f"<p>{escape(problem.description or 'No description available.')}</p>"
        
        # Get all contest problems for navigation
        all_problems = list(
            self.contest.contest_problems.order_by('order').values_list('problem__code', flat=True)
        )
        current_index = all_problems.index(problem.code) if problem.code in all_problems else -1
        next_problem = all_problems[current_index + 1] if current_index >= 0 and current_index < len(all_problems) - 1 else None
        
        return JsonResponse({
            'code': problem.code,
            'name': problem.name,
            'points': cp.points,
            'partial': cp.partial,
            'time_limit': problem.time_limit,
            'memory_limit': problem.memory_limit,
            'description_html': description_html,
            'languages': languages,
            'current_index': current_index,
            'total_problems': len(all_problems),
            'next_problem': next_problem,
        })


class HPECodeSubmitView(HPEContestAccessMixin, View):
    """Handle code submissions within HPE contest context."""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        problem_code = self.kwargs.get('problem_code')
        language_id = data.get('language')
        source_code = data.get('source', '')
        is_test_run = data.get('is_test_run', False)
        
        if not source_code.strip():
            return JsonResponse({'error': 'Source code is required'}, status=400)
        
        # Get problem and validate
        try:
            cp = ContestProblem.objects.select_related('problem').get(
                contest=self.contest,
                problem__code=problem_code
            )
            problem = cp.problem
        except ContestProblem.DoesNotExist:
            return JsonResponse({'error': 'Problem not found in contest'}, status=404)
        
        # Get language
        try:
            language = Language.objects.get(id=language_id)
        except Language.DoesNotExist:
            return JsonResponse({'error': 'Invalid language'}, status=400)
        
        # Create submission
        from judge.models import ContestSubmission, ContestParticipation
        
        # Get or create participation
        participation, _ = ContestParticipation.objects.get_or_create(
            contest=self.contest,
            user=request.user.profile,
            defaults={'virtual': 0}
        )
        
        # Create the submission
        submission = Submission.objects.create(
            user=request.user.profile,
            problem=problem,
            language=language,
            source=source_code,
            is_pretested=self.contest.run_pretests_only
        )
        
        # Link to contest if not a test run
        if not is_test_run:
            ContestSubmission.objects.create(
                submission=submission,
                problem=cp,
                participation=participation
            )
        
        # Trigger judging
        submission.judge(rejudge=False)
        
        return JsonResponse({
            'submission': submission.id,
            'message': 'Submission queued for judging'
        })


class HPESubmissionStatusView(HPEContestAccessMixin, View):
    """Poll submission status for real-time feedback."""
    
    def get(self, request, *args, **kwargs):
        submission_id = self.kwargs.get('submission_id')
        
        try:
            submission = Submission.objects.get(id=submission_id, user=request.user.profile)
        except Submission.DoesNotExist:
            return JsonResponse({'error': 'Submission not found'}, status=404)
        
        # Check if grading is complete
        is_graded = submission.status not in ('QU', 'P', 'G')
        
        # Get test case results
        test_cases = []
        for case in submission.test_cases.all().order_by('case'):
            test_cases.append({
                'case': case.case,
                'status': case.status,
                'time': f"{case.time:.3f}s" if case.time else None,
                'memory': f"{case.memory}KB" if case.memory else None,
            })
        
        return JsonResponse({
            'id': submission.id,
            'status': submission.status,
            'status_display': submission.long_status,
            'is_graded': is_graded,
            'points': float(submission.points) if submission.points else 0,
            'total_points': float(submission.problem.points),
            'time': f"{submission.time:.3f}s" if submission.time else None,
            'memory': f"{submission.memory}KB" if submission.memory else None,
            'test_cases': test_cases,
        })


class HPEMCQContentView(HPEContestAccessMixin, View):
    """Return MCQ content as JSON for AJAX loading."""
    
    def get(self, request, *args, **kwargs):
        from judge.models.mcq import MCQQuestion
        from judge.models.contest import ContestMCQ
        
        mcq_id = self.kwargs.get('mcq_id')
        
        try:
            mcq = MCQQuestion.objects.get(id=mcq_id)
        except MCQQuestion.DoesNotExist:
            return JsonResponse({'error': 'MCQ not found'}, status=404)
        
        # Check this MCQ is part of the contest
        try:
            contest_mcq = ContestMCQ.objects.get(contest=self.contest, mcq_question=mcq)
        except ContestMCQ.DoesNotExist:
            return JsonResponse({'error': 'MCQ not found in this contest'}, status=404)
        
        # Get options (shuffled for fairness - use same seed per user)
        import random
        options = list(mcq.options.all().order_by('order', 'id'))
        seed = f"mcq:{mcq.id}:user:{request.user.id}"
        shuffler = random.Random(seed)
        shuffler.shuffle(options)
        
        options_data = []
        for opt in options:
            options_data.append({
                'id': opt.id,
                'text': opt.option_text,
            })
        
        return JsonResponse({
            'id': mcq.id,
            'title': mcq.code,
            'question_text': mcq.description,
            'question_type': mcq.question_type,  # 'SINGLE' or 'MULTIPLE'
            'points': contest_mcq.points,
            'options': options_data,
        })


class HPEMCQSubmitView(HPEContestAccessMixin, View):
    """Submit MCQ answer - supports both single-correct and multi-correct questions."""
    
    def post(self, request, *args, **kwargs):
        from judge.models.mcq import MCQQuestion, MCQOption, MCQSubmission
        from judge.models.contest import ContestMCQ
        import json
        
        mcq_id = self.kwargs.get('mcq_id')
        
        try:
            mcq = MCQQuestion.objects.get(id=mcq_id)
        except MCQQuestion.DoesNotExist:
            return JsonResponse({'error': 'MCQ not found'}, status=404)
        
        # Check MCQ is in contest
        try:
            contest_mcq = ContestMCQ.objects.get(contest=self.contest, mcq_question=mcq)
        except ContestMCQ.DoesNotExist:
            return JsonResponse({'error': 'MCQ not found in this contest'}, status=404)
        
        # Parse answer(s)
        try:
            data = json.loads(request.body)
            # Support both 'answer' (single) and 'answers' (array)
            answer_ids = data.get('answers') or ([data.get('answer')] if data.get('answer') else [])
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid request'}, status=400)
        
        if not answer_ids:
            return JsonResponse({'error': 'No answer provided'}, status=400)
        
        # Get selected options
        selected_options = []
        for answer_id in answer_ids:
            try:
                option = MCQOption.objects.get(id=answer_id, question=mcq)
                selected_options.append(option)
            except MCQOption.DoesNotExist:
                return JsonResponse({'error': f'Invalid answer option: {answer_id}'}, status=400)
        
        # Get or create participation (matches HPECodeSubmitView behavior)
        from judge.models.contest import ContestParticipation
        participation, _ = ContestParticipation.objects.get_or_create(
            contest=self.contest,
            user=request.user.profile,
            virtual=ContestParticipation.LIVE,
            defaults={'virtual': 0}
        )
        
        # Auto-heal: If profile.current_contest is missing, restore it
        if request.user.profile.current_contest is None and not participation.ended:
            request.user.profile.current_contest = participation
            request.user.profile.save(update_fields=['current_contest'])
        
        # Calculate correctness for multi-correct
        # For MULTIPLE: all selected must be correct AND all correct options must be selected
        if mcq.question_type == 'MULTIPLE':
            correct_option_ids = set(mcq.options.filter(is_correct=True).values_list('id', flat=True))
            selected_ids = set(o.id for o in selected_options)
            is_correct = correct_option_ids == selected_ids
        else:
            # For SINGLE: the one selected option must be correct
            is_correct = len(selected_options) == 1 and selected_options[0].is_correct
        
        # Calculate points earned
        points_earned = contest_mcq.points if is_correct else 0.0
        
        # Create a NEW submission for each attempt (separate entry for each submission - history)
        submission = MCQSubmission.objects.create(
            question=mcq,
            user=request.user.profile,
            participation=participation,
            contest_object=self.contest,  # Set the Contest link directly
            is_correct=is_correct,  # Store in DB for later scoring, but don't reveal to user
            points_earned=points_earned  # Store the points from ContestMCQ
        )
        
        # Add all selected options
        for option in selected_options:
            submission.selected_options.add(option)
        
        submission.save()
        
        # Update ContestMCQSubmission - only ONE entry per user+question+contest
        # This points to the latest submission for scoring purposes
        if participation:
            from judge.models.contest import ContestMCQSubmission
            
            ContestMCQSubmission.objects.update_or_create(
                mcq=contest_mcq,
                participation=participation,
                defaults={
                    'submission': submission,  # Update to point to latest MCQSubmission
                    'points': contest_mcq.points if is_correct else 0.0,
                    'is_correct': is_correct
                }
            )
        
        # Return success WITHOUT revealing correctness (contest mode - silent save)
        # Frontend will keep the selected options intact without showing any message
        return JsonResponse({
            'success': True,
            'saved_options': answer_ids  # Return which options were saved so UI can keep them selected
        })


class HPEContestJoinView(HPEContestAccessMixin, View):
    """Join contest - creates ContestParticipation and sets current_contest.
    Called when user clicks 'Start Exam'.
    """
    
    def post(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.utils import timezone
        from judge.models import ContestParticipation
        from judge.debug import get_contest_rejoin_debug
        
        contest = self.contest
        profile = request.user.profile
        
        # Check if contest is ongoing
        if not contest.started:
            return JsonResponse({
                'success': False,
                'error': 'Contest has not started yet.'
            }, status=400)
        
        # Check if banned
        if contest.banned_users.filter(id=profile.id).exists():
            return JsonResponse({
                'success': False,
                'error': 'You are banned from this contest.'
            }, status=403)
        
        # Check if already exited (unless debug mode)
        if not get_contest_rejoin_debug():
            if ContestParticipation.objects.filter(contest=contest, user=profile, has_exited=True).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'You have already submitted this contest and cannot rejoin.'
                }, status=403)
        
        # Get or create participation
        LIVE = ContestParticipation.LIVE
        try:
            participation = ContestParticipation.objects.get(
                contest=contest, user=profile, virtual=LIVE
            )
            created = False
            # Update real_start on rejoin (for debug/testing mode)
            participation.real_start = timezone.now()
            participation.has_exited = False  # Reset exit status
            participation.save(update_fields=['real_start', 'has_exited'])
        except ContestParticipation.DoesNotExist:
            participation = ContestParticipation.objects.create(
                contest=contest, user=profile, virtual=LIVE,
                real_start=timezone.now()
            )
            created = True
        
        # Handle randomization of problems/MCQs for this participation
        _handle_contest_randomization(participation)
        
        # Set as current contest - use update_fields to ensure it's saved properly
        profile.current_contest = participation
        profile.save(update_fields=['current_contest'])
        
        # Update contest user count
        contest._updating_stats_only = True
        contest.update_user_count()
        
        return JsonResponse({
            'success': True,
            'message': 'Joined contest successfully.',
            'already_joined': not created,
            'participation_id': participation.id
        })


class HPEContestLeaveView(HPEContestAccessMixin, View):
    """Leave contest - sets has_exited=True and removes current_contest.
    Called when user clicks 'Submit Test'.
    """
    
    def post(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from judge.models import ContestParticipation
        
        contest = self.contest
        profile = request.user.profile
        
        # Find participation directly (more robust than relying on current_contest)
        try:
            participation = ContestParticipation.objects.get(
                contest=contest,
                user=profile,
                virtual=ContestParticipation.LIVE
            )
        except ContestParticipation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No participation found for this contest.'
            }, status=400)
        
        # Mark as exited (prevents rejoining)
        participation.has_exited = True
        participation.save(update_fields=['has_exited'])
        
        # Calculate and store final scores (this aggregates code + MCQ scores)
        participation.recompute_results()
        
        # Remove from contest if this is the current one
        if profile.current_contest and profile.current_contest.id == participation.id:
            profile.remove_contest()
        
        return JsonResponse({
            'success': True,
            'message': 'Contest submitted successfully.'
        })


class HPEContestSubmissionsView(HPEContestAccessMixin, View):
    """Get all submissions for the current user in this contest.
    Returns source code and scores for sending to Proctor backend.
    """
    
    def get(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from judge.models import ContestParticipation, ContestSubmission
        from judge.models.submission import SubmissionSource
        
        contest = self.contest
        profile = request.user.profile
        
        # Get participation
        try:
            participation = ContestParticipation.objects.get(
                contest=contest,
                user=profile,
                virtual=ContestParticipation.LIVE
            )
        except ContestParticipation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No participation found for this contest.'
            }, status=400)
        
        # Get all code submissions for this participation
        submissions_data = []
        contest_submissions = ContestSubmission.objects.filter(
            participation=participation
        ).select_related('submission__language', 'problem__problem').order_by('-submission__date')
        
        # Keep only the latest submission per problem
        seen_problems = set()
        for cs in contest_submissions:
            problem_code = cs.problem.problem.code
            if problem_code in seen_problems:
                continue
            seen_problems.add(problem_code)
            
            # Get source code
            try:
                source = SubmissionSource.objects.get(submission=cs.submission)
                source_code = source.source
            except SubmissionSource.DoesNotExist:
                source_code = ""
            
            submissions_data.append({
                'problem_code': problem_code,
                'language': cs.submission.language.key,  # e.g., 'PY3', 'CPP17'
                'source_code': source_code,
                'dmoj_submission_id': cs.submission.id,
                'points': float(cs.points) if cs.points else 0.0,
            })
        
        # Recompute results to ensure MCQ scores are up-to-date
        # This is important because this endpoint is called BEFORE /leave/
        participation.recompute_results()
        
        # Refresh participation from DB to get updated scores
        participation.refresh_from_db()
        
        # Get participation scores
        format_data = participation.format_data or {}
        
        return JsonResponse({
            'success': True,
            'dmoj_user_id': request.user.id,
            'dmoj_username': request.user.username,
            'contest_key': contest.key,
            'contest_name': contest.name,
            'problem_score': float(participation.problem_score),
            'mcq_score': float(participation.mcq_score),
            'total_score': float(participation.score),
            'format_data': format_data,
            'submissions': submissions_data
        })
