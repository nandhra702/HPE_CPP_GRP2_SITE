from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Max, OuterRef, Subquery
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _, gettext_lazy

from judge.contest_format.base import BaseContestFormat
from judge.contest_format.registry import register_contest_format
from judge.utils.timedelta import nice_repr


@register_contest_format('default')
class DefaultContestFormat(BaseContestFormat):
    name = gettext_lazy('Default')

    @classmethod
    def validate(cls, config):
        if config is not None and (not isinstance(config, dict) or config):
            raise ValidationError('default contest expects no config or empty dict as config')

    def __init__(self, contest, config):
        super(DefaultContestFormat, self).__init__(contest, config)

    def update_participation(self, participation):
        cumtime = 0
        problem_points = 0
        problem_data = {}

        # Aggregate coding problem scores - USE LATEST SUBMISSION (not best)
        # Get the points from the submission with the maximum (most recent) date for each problem
        latest_submission_points = (
            participation.submissions
            .filter(problem_id=OuterRef('problem_id'))
            .order_by('-submission__date')
            .values('points')[:1]
        )
        
        for result in participation.submissions.values('problem_id').annotate(
                time=Max('submission__date'),
                points=Subquery(latest_submission_points),
        ):
            dt = (result['time'] - participation.start).total_seconds()
            if result['points']:
                cumtime += dt
            problem_data[str(result['problem_id'])] = {'time': dt, 'points': result['points'] or 0}
            problem_points += result['points'] or 0

        # Aggregate MCQ scores
        mcq_points = 0
        mcq_data = {}
        for mcq_sub in participation.contest_mcq_submissions.select_related('mcq').all():
            mcq_data[str(mcq_sub.mcq_id)] = {
                'points': mcq_sub.points,
                'is_correct': mcq_sub.is_correct
            }
            mcq_points += mcq_sub.points

        # Calculate total score
        total_points = problem_points + mcq_points

        # Build format_data with clear separation
        participation.format_data = {
            'problems': problem_data,
            'mcqs': mcq_data,
            'summary': {
                'problem_score': round(problem_points, self.contest.points_precision),
                'mcq_score': round(mcq_points, self.contest.points_precision),
                'total_score': round(total_points, self.contest.points_precision)
            }
        }

        participation.cumtime = max(cumtime, 0)
        participation.score = round(total_points, self.contest.points_precision)
        participation.problem_score = round(problem_points, self.contest.points_precision)
        participation.mcq_score = round(mcq_points, self.contest.points_precision)
        participation.tiebreaker = 0
        participation.save()

    def display_user_problem(self, participation, contest_problem):
        format_data = (participation.format_data or {}).get(str(contest_problem.id))
        if format_data:
            return format_html(
                '<td class="{state}"><a href="{url}">{points}<div class="solving-time">{time}</div></a></td>',
                state=(('pretest-' if self.contest.run_pretests_only and contest_problem.is_pretested else '') +
                       self.best_solution_state(format_data['points'], contest_problem.points)),
                url=reverse('contest_user_submissions',
                            args=[self.contest.key, participation.user.user.username, contest_problem.problem.code]),
                points=floatformat(format_data['points']),
                time=nice_repr(timedelta(seconds=format_data['time']), 'noday'),
            )
        else:
            return mark_safe('<td></td>')

    def display_participation_result(self, participation):
        return format_html(
            '<td class="user-points"><a href="{url}">{points}<div class="solving-time">{cumtime}</div></a></td>',
            url=reverse('contest_all_user_submissions',
                        args=[self.contest.key, participation.user.user.username]),
            points=floatformat(participation.score, -self.contest.points_precision),
            cumtime=nice_repr(timedelta(seconds=participation.cumtime), 'noday'),
        )

    def get_problem_breakdown(self, participation, contest_problems):
        return [(participation.format_data or {}).get(str(contest_problem.id)) for contest_problem in contest_problems]

    def get_label_for_problem(self, index):
        return str(index + 1)

    def get_short_form_display(self):
        yield _('The latest submission for each problem will be used for scoring.')
        yield _('Ties will be broken by the sum of the last submission time on problems with a non-zero score.')
