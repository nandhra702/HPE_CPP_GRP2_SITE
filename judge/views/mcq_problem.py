from django.shortcuts import render, get_object_or_404
from judge.models.problem import Problem
from judge.models.mcq_problem import MCQProblem

def mcq_problem_detail(request, code):
    problem = get_object_or_404(MCQProblem, code=code)
    options = problem.options.all()  

    return render(request, "problem/mcq_detail.html", {
        "problem": problem,
        "options": options
    })
