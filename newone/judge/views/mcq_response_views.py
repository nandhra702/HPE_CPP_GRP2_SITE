from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from judge.models.mcq_problem import MCQProblem
from judge.models.mcq_problem import MCQOption
from judge.models.mcq_response import MCQResponse

@login_required
def submit_mcq_response(request, code):
    if request.method != "POST":
        return redirect("mcq_problem_detail", code=code)

    problem = get_object_or_404(MCQProblem, code=code)
    selected_option_id = request.POST.get("selected_option")

    if not selected_option_id:
        messages.error(request, "No option selected!")
        return redirect("mcq_problem_detail", code=code)

    selected_option = get_object_or_404(MCQOption, id=selected_option_id, problem_id=problem.id)
    is_correct = selected_option.is_correct

    # Save the response
    MCQResponse.objects.update_or_create(
        user=request.user,
        problem=problem,
        defaults={
            "option": selected_option,
            "is_correct": is_correct
        }
    )

    return redirect("mcq_problem_detail", code=code)
