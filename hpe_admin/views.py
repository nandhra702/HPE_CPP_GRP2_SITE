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
