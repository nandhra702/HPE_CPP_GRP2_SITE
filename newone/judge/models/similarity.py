from django.db import models
from django.conf import settings
from .contest import Contest  # adjust path as needed

class SimilarityScore(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    problem_code = models.CharField(max_length=100)
    similarity_percent = models.FloatField()

    class Meta:
        unique_together = ('contest', 'user', 'problem_code')

    def __str__(self):
        return f"{self.user.username} - {self.problem_code} - {self.similarity_percent:.2f}%"