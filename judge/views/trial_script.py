from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from django.db import connection
from collections import defaultdict

from judge.models import Contest, LatestSubmission, LatestSubmissionPG


# -----------------------------------------------------------
# Populate the LatestSubmission table (SQLite)
# -----------------------------------------------------------

def populate_latest_submissions(contest_key, only_ac=True):
    contest = Contest.objects.get(key=contest_key)

    LatestSubmission.objects.filter(contest=contest).delete()

    where_clause = "AND s.result = 'AC'" if only_ac else ""


    query = f"""
    SELECT
        s.id,
        s.user_id,
        s.problem_id,
        s.language_id,
        src.source,
        u.username
    FROM judge_submission s
    JOIN (
        SELECT user_id, problem_id, MAX(id) AS max_id
        FROM judge_submission s2
        WHERE s2.contest_object_id = %s { "AND s2.result = 'AC'" if only_ac else "" }
        GROUP BY user_id, problem_id
    ) latest ON latest.max_id = s.id
    JOIN judge_submissionsource src ON src.submission_id = s.id
    JOIN auth_user u ON u.id = s.user_id
    WHERE s.contest_object_id = %s
"""

    with connection.cursor() as cursor:
        cursor.execute(query, [contest.id, contest.id])
        rows = cursor.fetchall()

    objs = []
    for submission_id, user_id, problem_id, language_id, source, username in rows:
        objs.append(
            LatestSubmission(
                submission_id=submission_id,
                user_id=user_id,
                contest=contest,
                problem_id=problem_id,
                language_id=language_id,
                source=source,
                username=username,
            )
        )

    LatestSubmission.objects.bulk_create(objs, ignore_conflicts=True)



# -----------------------------------------------------------
# Export to PostgreSQL (your final requirement)
# -----------------------------------------------------------

def export_contest_data(request, contest_key):
    contest = Contest.objects.get(key=contest_key)

    if not request.user.is_authenticated or not contest.authors.filter(id=request.user.id).exists():
        return HttpResponseForbidden("Not allowed")

    # Step 1: populate SQLite table
    populate_latest_submissions(contest_key)

    # Step 2: read from SQLite
    rows = LatestSubmission.objects.filter(contest=contest)

    # Step 3: write to PostgreSQL
    pg_rows = []
    for r in rows:
        pg_rows.append(
            LatestSubmissionPG(
                submission_id=r.submission_id,
                user_id=r.user_id,
                contest_id=r.contest_id,
                problem_id=r.problem_id,
                language_id=r.language_id,
                source=r.source,
                username=r.username,
                updated_at=timezone.now(),
            )
        )

    LatestSubmissionPG.objects.using('postgres').bulk_create(pg_rows, ignore_conflicts=True)

    return render(request, 'contest/export_success.html', {
        "contest": contest,
        "count": len(pg_rows)
    })
