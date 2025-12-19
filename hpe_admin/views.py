from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.http import Http404

from judge.models import Contest

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
    # This is the old portal, keeping for backward compat or redirection?
    # Actually, user wants the NEW flow.
    # Let's redirect this to Check View if it's the entry point.
    def get(self, request, *args, **kwargs):
        return redirect('hpe_contest_check', contest_key=self.contest.key)

class HPEContestCheckView(HPEContestAccessMixin, DetailView):
    template_name = 'hpe_admin/system_check.html'
    
    def get_object(self, queryset=None):
        return self.contest

class HPEContestIntroView(HPEContestAccessMixin, DetailView):
    template_name = 'hpe_admin/instructions.html'
    
    def get_object(self, queryset=None):
        return self.contest

class HPEContestExamView(HPEContestAccessMixin, DetailView):
    template_name = 'hpe_admin/exam_dashboard.html'
    
    def get_object(self, queryset=None):
        return self.contest

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
        
        # Get participation
        from judge.models.contest import ContestParticipation
        try:
            participation = ContestParticipation.objects.get(
                contest=self.contest,
                user=request.user.profile,
                virtual=ContestParticipation.LIVE
            )
        except ContestParticipation.DoesNotExist:
            participation = None
        
        # Calculate correctness for multi-correct
        # For MULTIPLE: all selected must be correct AND all correct options must be selected
        if mcq.question_type == 'MULTIPLE':
            correct_option_ids = set(mcq.options.filter(is_correct=True).values_list('id', flat=True))
            selected_ids = set(o.id for o in selected_options)
            is_correct = correct_option_ids == selected_ids
        else:
            # For SINGLE: the one selected option must be correct
            is_correct = len(selected_options) == 1 and selected_options[0].is_correct
        
        # Create or update submission
        submission, created = MCQSubmission.objects.get_or_create(
            question=mcq,
            user=request.user.profile,
            participation=participation,
            defaults={'is_correct': is_correct}
        )
        
        if not created:
            # Update existing submission
            submission.selected_options.clear()
        
        # Add all selected options
        for option in selected_options:
            submission.selected_options.add(option)
        
        submission.is_correct = is_correct
        submission.save()
        
        return JsonResponse({
            'success': True,
            'correct': is_correct,
            'message': 'Answer saved'
        })
