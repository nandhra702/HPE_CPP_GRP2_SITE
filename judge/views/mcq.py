import logging
import random
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, F, Q, Case, When, BooleanField, Prefetch
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _, gettext_lazy
from django.views.generic import DetailView, ListView, View
from django.views.generic.detail import SingleObjectMixin

from judge.models import MCQQuestion, MCQOption, MCQSubmission, ProblemGroup, ProblemType, Profile
from judge.utils.diggpaginator import DiggPaginator
from judge.utils.views import QueryStringSortMixin, TitleMixin, generic_message

__all__ = ['MCQList', 'MCQDetail', 'MCQSubmitView']


class MCQMixin(object):
    model = MCQQuestion
    slug_url_kwarg = 'mcq'
    slug_field = 'code'

    def get_object(self, queryset=None):
        mcq = super(MCQMixin, self).get_object(queryset)
        if not mcq.is_public and not self.request.user.is_authenticated:
            raise Http404()
        if not mcq.is_public and not mcq.is_editable_by(self.request.user):
            # Check if user is in organization
            if mcq.is_organization_private:
                if not mcq.organizations.filter(id__in=self.request.profile.organizations.all()).exists():
                    raise Http404()
            else:
                raise Http404()
        return mcq

    def no_such_mcq(self):
        code = self.kwargs.get(self.slug_url_kwarg, None)
        return generic_message(self.request, _('No such MCQ'),
                               _('Could not find an MCQ question with the code "%s".') % code, status=404)

    def get(self, request, *args, **kwargs):
        try:
            return super(MCQMixin, self).get(request, *args, **kwargs)
        except Http404:
            return self.no_such_mcq()


class SolvedMCQMixin(object):
    def get_completed_mcqs(self):
        if self.in_contest:
            # Get completed MCQs in this contest
            participation = self.profile.current_contest
            return set(MCQSubmission.objects.filter(
                user=self.profile,
                is_correct=True,
                participation=participation
            ).values_list('question_id', flat=True))
        elif self.profile is not None:
            return set(MCQSubmission.objects.filter(
                user=self.profile,
                is_correct=True,
                participation__isnull=True  # Only non-contest submissions
            ).values_list('question_id', flat=True))
        return set()

    def get_attempted_mcqs(self):
        if self.in_contest:
            # Get attempted MCQs in this contest
            participation = self.profile.current_contest
            return set(MCQSubmission.objects.filter(
                user=self.profile,
                participation=participation
            ).values_list('question_id', flat=True))
        elif self.profile is not None:
            return set(MCQSubmission.objects.filter(
                user=self.profile,
                participation__isnull=True  # Only non-contest submissions
            ).values_list('question_id', flat=True))
        return set()

    @cached_property
    def profile(self):
        if not self.request.user.is_authenticated:
            return None
        return self.request.profile
    
    @cached_property
    def in_contest(self):
        return self.profile is not None and self.profile.current_contest is not None
    
    @cached_property
    def contest(self):
        return self.profile.current_contest.contest if self.in_contest else None


class MCQList(QueryStringSortMixin, TitleMixin, SolvedMCQMixin, ListView):
    model = MCQQuestion
    title = gettext_lazy('MCQ Questions')
    context_object_name = 'mcqs'
    template_name = 'mcq/list.html'
    paginate_by = 50
    sql_sort = frozenset(('points', 'ac_rate', 'user_count', 'code'))
    manual_sort = frozenset(('name', 'group', 'solved', 'type'))
    all_sorts = sql_sort | manual_sort
    default_desc = frozenset(('points', 'ac_rate', 'user_count'))
    default_sort = 'code'

    def get_paginator(self, queryset, per_page, orphans=0,
                      allow_empty_first_page=True, **kwargs):
        # In contest mode, queryset is a list, so handle differently
        if isinstance(queryset, list):
            count = len(queryset)
        else:
            count = queryset.values('pk').count()
            
        paginator = DiggPaginator(queryset, per_page, body=6, padding=2, orphans=orphans,
                                  count=count,
                                  allow_empty_first_page=allow_empty_first_page, **kwargs)
        
        sort_key = self.order.lstrip('-')
        if not isinstance(queryset, list) and sort_key in self.sql_sort:
            queryset = queryset.order_by(self.order, 'id')
        elif sort_key == 'name':
            queryset = queryset.order_by(self.order, 'id')
        elif sort_key == 'group':
            queryset = queryset.order_by(self.order + '__name', 'id')
        elif sort_key == 'solved':
            if self.request.user.is_authenticated:
                completed = self.get_completed_mcqs()
                attempted = self.get_attempted_mcqs()

                def _solved_sort_order(mcq):
                    if mcq.id in completed:
                        return 1
                    if mcq.id in attempted:
                        return 0
                    return -1

                queryset = list(queryset)
                queryset.sort(key=_solved_sort_order, reverse=self.order.startswith('-'))
        elif sort_key == 'type':
            if self.show_types:
                queryset = list(queryset)
                queryset.sort(key=lambda mcq: mcq.types_list[0] if mcq.types_list else '',
                              reverse=self.order.startswith('-'))
        
        paginator.object_list = queryset
        return paginator

    @cached_property
    def profile(self):
        if not self.request.user.is_authenticated:
            return None
        return self.request.profile

    def get_contest_queryset(self):
        """Get MCQs for the current contest"""
        from judge.models import ContestMCQ
        
        # Get the MCQ IDs that are in this contest
        contest_mcq_data = ContestMCQ.objects.filter(
            contest=self.contest
        ).values('mcq_question_id', 'points', 'order')
        
        # Create a dict for quick lookup of contest data
        contest_data = {cm['mcq_question_id']: {'points': cm['points'], 'order': cm['order']} 
                       for cm in contest_mcq_data}
        mcq_ids = list(contest_data.keys())

        # Filter randomized MCQs
        if self.profile and self.profile.current_contest and self.profile.current_contest.contest_id == self.contest.id:
            participation = self.profile.current_contest
            if participation.format_data and 'selected_mcqs' in participation.format_data:
                selected_ids = set(participation.format_data['selected_mcqs'])
                mcq_ids = [mid for mid in mcq_ids if mid in selected_ids]
        
        # Get the actual MCQQuestion objects
        queryset = MCQQuestion.objects.filter(
            id__in=mcq_ids
        ).select_related('group').prefetch_related('options')
        
        # Annotate each MCQ with its contest-specific data
        mcqs = list(queryset)
        for mcq in mcqs:
            mcq.contest_points = contest_data[mcq.id]['points']
            mcq.contest_order = contest_data[mcq.id]['order']
        
        # Sort by contest order
        mcqs.sort(key=lambda x: x.contest_order)
        
        return mcqs

    def get_normal_queryset(self):
        """Get MCQs for normal (non-contest) viewing"""
        filter = Q(is_public=True)
        if self.profile is not None:
            # Include questions user is author/curator of
            filter |= Q(authors=self.profile) | Q(curators=self.profile)
            # Include organization private questions if user is in organization
            filter |= Q(is_organization_private=True, organizations__in=self.profile.organizations.all())
        
        queryset = MCQQuestion.objects.filter(filter).select_related('group').prefetch_related('options').distinct()
        
        if self.profile is not None and self.hide_solved:
            completed = self.get_completed_mcqs()
            queryset = queryset.exclude(id__in=completed)
        
        queryset = queryset.prefetch_related('types')
        
        if self.category is not None:
            queryset = queryset.filter(group__id=self.category)
        
        if self.selected_types:
            queryset = queryset.filter(types__in=self.selected_types)
            
        if self.format:
            queryset = queryset.filter(question_type=self.format)
        
        if self.search_query:
            queryset = queryset.filter(
                Q(code__icontains=self.search_query) |
                Q(name__icontains=self.search_query) |
                Q(description__icontains=self.search_query)
            )
        
        return queryset

    def get_queryset(self):
        if self.in_contest:
            return self.get_contest_queryset()
        else:
            return self.get_normal_queryset()

    def get_context_data(self, **kwargs):
        context = super(MCQList, self).get_context_data(**kwargs)
        
        # In contest mode, show different UI
        if self.in_contest:
            context['in_contest'] = True
            context['contest'] = self.contest
            context['hide_solved'] = 0
            context['show_types'] = 0
            context['category'] = None
            context['search_query'] = ''
            # Provide empty sort context for contest mode (sorting disabled but links still needed)
            context['sort_links'] = {
                'solved': '#',
                'name': '#',
                'group': '#',
                'type': '#',
                'points': '#',
                'ac_rate': '#',
                'user_count': '#'
            }
            context['sort_order'] = {
                'solved': '',
                'name': '',
                'group': '',
                'type': '',
                'points': '',
                'ac_rate': '',
                'user_count': ''
            }
        else:
            context['in_contest'] = False
            context['hide_solved'] = int(self.hide_solved)
            context['show_types'] = 1
            context['category'] = self.category
            context['categories'] = ProblemGroup.objects.all()
            context['format'] = self.format
            
            context['selected_types'] = self.selected_types
            context['mcq_types'] = ProblemType.objects.all()
            
            context['search_query'] = self.search_query
            
            # Add sorting context
            context.update(self.get_sort_context())
        
        context['completed_mcq_ids'] = self.get_completed_mcqs()
        context['attempted_mcqs'] = self.get_attempted_mcqs()
        
        return context

    def setup(self, request, *args, **kwargs):
        super(MCQList, self).setup(request, *args, **kwargs)
        self.hide_solved = request.GET.get('hide_solved') == '1'
        self.show_types = True
        self.category = request.GET.get('category')
        if self.category:
            try:
                self.category = int(self.category)
            except ValueError:
                self.category = None
        # Convert selected types to integers for comparison in template
        self.selected_types = []
        for type_id in request.GET.getlist('type'):
            try:
                self.selected_types.append(int(type_id))
            except (ValueError, TypeError):
                pass
        self.search_query = ''
        self.format = request.GET.get('format')
        if self.format not in ['SINGLE', 'MULTIPLE']:
            self.format = None


class MCQDetail(MCQMixin, SolvedMCQMixin, TitleMixin, DetailView):
    context_object_name = 'mcq'
    template_name = 'mcq/detail.html'

    def get_title(self):
        return self.object.name

    def get_context_data(self, **kwargs):
        context = super(MCQDetail, self).get_context_data(**kwargs)
        user = self.request.user
        
        context['completed_mcq_ids'] = self.get_completed_mcqs()
        context['attempted_mcqs'] = self.get_attempted_mcqs()
        context['can_edit_mcq'] = self.object.is_editable_by(user) if user.is_authenticated else False
        
        # Add contest mode flags
        context['in_contest'] = self.in_contest
        context['show_answer'] = True  # Default to showing answers
        
        # Get user's submission if exists - filter by contest context
        if user.is_authenticated:
            try:
                # Check if user is in a contest
                if self.in_contest:
                    # Get submission for current contest
                    participation = self.profile.current_contest
                    submission = MCQSubmission.objects.get(
                        question=self.object, 
                        user=user.profile,
                        participation=participation
                    )
                    # Don't show answers during active contest
                    context['show_answer'] = participation.ended
                else:
                    # Get regular (non-contest) submission
                    submission = MCQSubmission.objects.get(
                        question=self.object, 
                        user=user.profile,
                        participation__isnull=True
                    )
                context['user_submission'] = submission
                context['selected_option_ids'] = list(submission.selected_options.values_list('id', flat=True))
            except MCQSubmission.DoesNotExist:
                context['user_submission'] = None
                context['selected_option_ids'] = []
        else:
            context['user_submission'] = None
            context['selected_option_ids'] = []
        
        # Get options and always present them in a user-specific random order
        options = list(self.object.options.all().order_by('order', 'id'))
        seed_parts = [f"question:{self.object.pk}"]
        if user.is_authenticated:
            seed_parts.append(f"user:{user.pk}")
        else:
            session_key = self.request.session.session_key
            if session_key is None:
                self.request.session.setdefault('mcq_seed_initialized', True)
                self.request.session.save()
                session_key = self.request.session.session_key
            seed_parts.append(f"session:{session_key}")
        shuffler = random.Random('|'.join(seed_parts))
        shuffler.shuffle(options)
        context['options'] = options
        
        return context


class MCQSubmitView(LoginRequiredMixin, MCQMixin, SolvedMCQMixin, SingleObjectMixin, View):
    """Handle MCQ answer submission - supports both contest and normal modes with auto-save"""
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Get selected options (can be empty for clearing answer)
        selected_option_ids = request.POST.getlist('options')
        
        # Validate selected options belong to this question (if any selected)
        if selected_option_ids:
            selected_options = MCQOption.objects.filter(
                id__in=selected_option_ids,
                question=self.object
            )
            
            if selected_options.count() != len(selected_option_ids):
                return JsonResponse({
                    'success': False,
                    'error': _('Invalid option selected.')
                })
        else:
            # No options selected - will clear the answer or result in 0 points
            selected_options = MCQOption.objects.none()
        
        # Check if user is in a contest
        in_contest = self.in_contest
        participation = self.profile.current_contest if in_contest else None
        contest = self.contest if in_contest else None
        
        # Get or check ContestMCQ if in contest
        contest_mcq = None
        if in_contest and contest:
            from judge.models import ContestMCQ
            try:
                contest_mcq = ContestMCQ.objects.get(contest=contest, mcq_question=self.object)
            except ContestMCQ.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': _('This MCQ is not part of the current contest.')
                })
        
        # Create or update submission based on context
        with transaction.atomic():
            if in_contest and contest_mcq:
                # Contest mode: Use get_or_create to allow answer updates
                submission, created = MCQSubmission.objects.get_or_create(
                    question=self.object,
                    user=request.profile,
                    participation=participation,
                    contest_object=contest_mcq
                )
                
                # Update selected options (allows changing answer)
                submission.selected_options.set(selected_options)
                
                # Use contest points for scoring
                self.object.points = contest_mcq.points
                submission.calculate_score()
                
            else:
                # Normal mode: Check if already submitted
                existing_submission = MCQSubmission.objects.filter(
                    question=self.object,
                    user=request.profile,
                    participation__isnull=True
                ).first()
                
                if existing_submission:
                    return JsonResponse({
                        'success': False,
                        'error': _('You have already submitted an answer for this question.')
                    })
                
                # Create new submission
                submission = MCQSubmission.objects.create(
                    question=self.object,
                    user=request.profile
                )
                submission.selected_options.set(selected_options)
                submission.calculate_score()
        
        # Update question statistics (only for non-contest or after contest ends)
        if not in_contest:
            self.object.user_count = MCQSubmission.objects.filter(
                question=self.object, 
                is_correct=True,
                participation__isnull=True
            ).count()
            total_submissions = MCQSubmission.objects.filter(
                question=self.object,
                participation__isnull=True
            ).count()
            if total_submissions > 0:
                self.object.ac_rate = (self.object.user_count / total_submissions) * 100
            self.object.save(update_fields=['user_count', 'ac_rate'])
        
        # Determine if we should show the answer
        show_answer = True
        if in_contest and contest_mcq:
            # Don't show answer during active contest
            show_answer = participation.ended if participation else False
        
        return JsonResponse({
            'success': True,
            'is_correct': submission.is_correct,
            'points_earned': submission.points_earned,
            'show_answer': show_answer,
            'in_contest': in_contest
        })


class MCQFinalSubmitView(LoginRequiredMixin, View):
    """
    Handle final MCQ submission when user clicks "Leave Contest" or time expires.
    Calculates final score and locks submissions.
    """
    
    def post(self, request, contest):
        from judge.models.contest import Contest, ContestMCQResult
        from django.utils import timezone
        
        try:
            contest_obj = Contest.objects.get(key=contest)
        except Contest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Contest not found'
            }, status=404)
        
        # Get current participation
        participation = request.profile.current_contest
        if not participation or participation.contest.key != contest:
            return JsonResponse({
                'success': False,
                'error': 'You are not participating in this contest'
            }, status=400)
        
        # Check if already submitted
        existing_result = ContestMCQResult.objects.filter(
            user=request.profile,
            contest=contest_obj
        ).first()
        
        if existing_result and existing_result.is_final:
            return JsonResponse({
                'success': False,
                'error': 'You have already submitted your final answers',
                'score': float(existing_result.score),
                'correct': existing_result.correct,
                'wrong': existing_result.wrong,
                'attempted': existing_result.attempted,
                'total_questions': existing_result.total_questions
            }, status=400)
        
        # Create or get result object
        result, created = ContestMCQResult.objects.get_or_create(
            user=request.profile,
            contest=contest_obj,
            defaults={
                'participation': participation
            }
        )
        
        # Calculate final score
        final_score = result.calculate_score()
        
        # Mark as final and set submission time
        result.is_final = True
        result.submitted_at = timezone.now()
        result.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Final submission successful! Your answers have been locked.',
            'score': float(result.score),
            'correct': result.correct,
            'wrong': result.wrong,
            'attempted': result.attempted,
            'total_questions': result.total_questions,
            'is_final': True
        })
