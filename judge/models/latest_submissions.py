from django.db import models
from django.contrib.auth.models import User


class LatestSubmission(models.Model):
    submission_id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey('Contest', null=True, on_delete=models.SET_NULL)
    problem_id = models.IntegerField()
    language_id = models.IntegerField()       # <-- NEW
    source = models.TextField(null=True)
    username = models.CharField(max_length=150)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'latest_submissionsMB'  # To avoid conflict with Postgres table
