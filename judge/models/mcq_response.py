from django.db import models
from django.contrib.auth.models import User
from judge.models.mcq_problem import MCQProblem
from judge.models.mcq_problem import MCQOption

class MCQResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(MCQProblem, on_delete=models.CASCADE)
    option = models.ForeignKey(MCQOption, on_delete=models.CASCADE)
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "problem")  # one submission per user per problem

    def __str__(self):
        return f"{self.user.username} - {self.problem.name} - {'correct' if self.is_correct else 'wrong'}"
