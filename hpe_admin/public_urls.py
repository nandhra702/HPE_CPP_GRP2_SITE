from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.HPEContestLoginView.as_view(), name='hpe_contest_login'),
    # Redirect entry point
    path('contest/<str:contest_key>/', views.HPEContestView.as_view(), name='hpe_contest_view'),
    # New Pipeline Steps
    path('contest/<str:contest_key>/check/', views.HPEContestCheckView.as_view(), name='hpe_contest_check'),
    path('contest/<str:contest_key>/intro/', views.HPEContestIntroView.as_view(), name='hpe_contest_intro'),
    path('contest/<str:contest_key>/exam/', views.HPEContestExamView.as_view(), name='hpe_contest_exam'),
    # AJAX Content
    path('contest/<str:contest_key>/problem/<str:problem_code>/content/', views.HPEProblemContentAjaxView.as_view(), name='hpe_problem_content_ajax'),
    # Code Submission
    path('contest/<str:contest_key>/problem/<str:problem_code>/submit/', views.HPECodeSubmitView.as_view(), name='hpe_code_submit'),
    # Submission Status Polling
    path('contest/<str:contest_key>/submission/<int:submission_id>/status/', views.HPESubmissionStatusView.as_view(), name='hpe_submission_status'),
]

