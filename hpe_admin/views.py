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

class HPEContestView(LoginRequiredMixin, DetailView):
    model = Contest
    template_name = 'hpe_admin/contest_portal.html'
    context_object_name = 'contest'
    login_url = reverse_lazy('hpe_contest_login')
    
    def get_object(self, queryset=None):
        key = self.kwargs.get('contest_key')
        contest = get_object_or_404(Contest, key=key)
        return contest
        
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        contest = self.get_object()
        
        # Access Check Logic
        # 1. Admins/Creators always allow
        if request.user.has_perm('judge.edit_all_contest') or \
           request.user.profile in contest.authors.all() or \
           request.user.profile in contest.curators.all():
            return super().dispatch(request, *args, **kwargs)
            
        # 2. Private Contestants
        if contest.private_contestants.filter(id=request.user.profile.id).exists():
            return super().dispatch(request, *args, **kwargs)
            
        # Deny otherwise
        # Render custom 403 or denial page to keep isolation
        return render(request, 'hpe_admin/access_denied.html', {'contest': contest}, status=403)

