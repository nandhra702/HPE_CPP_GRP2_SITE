from .sites import HPEAdminSite
from judge.models import Problem, MCQQuestion
from judge.admin.problem import ProblemAdmin
from judge.admin.mcq import MCQQuestionAdmin

hpe_admin_site = HPEAdminSite(name='hpe_admin')

hpe_admin_site.register(Problem, ProblemAdmin)
hpe_admin_site.register(MCQQuestion, MCQQuestionAdmin)
