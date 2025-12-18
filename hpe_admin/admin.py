from .sites import HPEAdminSite
from judge.models import Problem
from judge.admin.problem import ProblemAdmin

hpe_admin_site = HPEAdminSite(name='hpe_admin')

hpe_admin_site.register(Problem, ProblemAdmin)
