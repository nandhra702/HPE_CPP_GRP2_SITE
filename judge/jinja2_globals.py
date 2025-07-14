from django_jinja import library
from collections import defaultdict
from judge.models import ContestSubmission

@library.global_function
def problem_languages_for(contest):
    result = defaultdict(set)
    qs = ContestSubmission.objects.select_related(
        'submission__language', 'problem__problem', 'problem__contest'
    ).filter(problem__contest=contest)

    for entry in qs:
        code = entry.problem.problem.code
        lang = entry.submission.language.name
        result[code].add(lang)

    return dict(result)
