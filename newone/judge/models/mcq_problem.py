from django.db import models
from django.utils.translation import gettext_lazy as _

class MCQProblem(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)
    question_text = models.TextField()
    is_public = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_mcq(self):
        return True


class MCQOption(models.Model):
    problem = models.ForeignKey(MCQProblem, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text
