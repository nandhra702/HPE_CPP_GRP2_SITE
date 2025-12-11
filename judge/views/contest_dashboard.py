from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from judge.models import Problem, MCQQuestion, ProblemType, ProblemGroup

@staff_member_required
@require_GET
def contest_dashboard(request):
    return render(request, 'admin/judge/contest/dashboard.html')

@staff_member_required
@require_GET
def contest_dashboard_api(request):
    # Parameters
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 25))
    search = request.GET.get('search', '')
    category = request.GET.get('category', '') # Easy, Medium, Hard (mapped to group or type)
    p_type = request.GET.get('type', '')
    is_mcq = request.GET.get('is_mcq', 'false') == 'true'
    
    if is_mcq:
        queryset = MCQQuestion.objects.all()
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) | 
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        if category:
            # Try matching group or type
            queryset = queryset.filter(
                Q(group__name__iexact=category) | 
                Q(group__full_name__iexact=category) |
                Q(types__name__iexact=category) |
                Q(types__full_name__iexact=category)
            ).distinct()
        
        if p_type:
             queryset = queryset.filter(types__id=p_type)

        # Additional MCQ filters
        mcq_format = request.GET.get('format', '')
        if mcq_format:
            queryset = queryset.filter(question_type=mcq_format)

        paginator = Paginator(queryset.order_by('code'), limit)
        page_obj = paginator.get_page(page)
        
        data = {
            'items': [{
                'id': q.id,
                'code': q.code,
                'name': q.name,
                'points': q.points,
                'type': q.question_type,
                'group': q.group.full_name if q.group else 'Uncategorized',
                'types': [t.name for t in q.types.all()]
            } for q in page_obj],
            'total': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page
        }
    else:
        queryset = Problem.objects.all()
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) | 
                Q(name__icontains=search)
            )
        
        if category:
            # User requested filtering by "Easy", "Medium", "Hard"
            # We check if they match a group or type name
            queryset = queryset.filter(
                Q(group__name__iexact=category) | 
                Q(group__full_name__iexact=category) |
                Q(types__name__iexact=category) |
                Q(types__full_name__iexact=category)
            ).distinct()

        if p_type:
            queryset = queryset.filter(types__id=p_type)

        paginator = Paginator(queryset.order_by('code'), limit)
        page_obj = paginator.get_page(page)

        data = {
            'items': [{
                'id': p.id,
                'code': p.code,
                'name': p.name,
                'points': p.points,
                'group': p.group.full_name if p.group else 'Uncategorized',
                'types': [t.name for t in p.types.all()]
            } for p in page_obj],
            'total': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page
        }

    return JsonResponse(data)

@staff_member_required
@require_GET
def contest_dashboard_metadata(request):
    # Return available types and groups for filters
    types = ProblemType.objects.values('id', 'name', 'full_name')
    groups = ProblemGroup.objects.values('id', 'name', 'full_name')
    return JsonResponse({
        'types': list(types),
        'groups': list(groups)
    })
