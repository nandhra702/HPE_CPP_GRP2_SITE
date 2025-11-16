from django.db import models

class LatestSubmissionPG(models.Model):
    submission_id = models.IntegerField(primary_key=True)
    user_id = models.IntegerField()
    contest_id = models.IntegerField()
    problem_id = models.IntegerField()
    language_id = models.IntegerField()
    source = models.TextField(null=True)
    username = models.CharField(max_length=150)
    updated_at = models.DateTimeField()

    class Meta:
        managed = False       # IMPORTANT
        db_table = 'latest_submissions'
