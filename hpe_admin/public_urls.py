from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.HPEContestLoginView.as_view(), name='hpe_contest_login'),
    # Landing page with inline login
    path('contest/<str:contest_key>/', views.HPEContestLandingView.as_view(), name='hpe_contest_landing'),
    # Seamless logout (for account switching)
    path('contest/<str:contest_key>/logout/', views.HPEContestLogoutView.as_view(), name='hpe_contest_logout'),

    # New Pipeline Steps


    # Exam content for SPA loading (returns HTML fragment)
    path('contest/<str:contest_key>/exam/content/', views.HPEExamContentView.as_view(), name='hpe_exam_content'),
    # AJAX Content
    path('contest/<str:contest_key>/problem/<str:problem_code>/content/', views.HPEProblemContentAjaxView.as_view(), name='hpe_problem_content_ajax'),
    # Code Submission
    path('contest/<str:contest_key>/problem/<str:problem_code>/submit/', views.HPECodeSubmitView.as_view(), name='hpe_code_submit'),
    # Submission Status Polling
    path('contest/<str:contest_key>/submission/<int:submission_id>/status/', views.HPESubmissionStatusView.as_view(), name='hpe_submission_status'),
    # MCQ AJAX
    path('contest/<str:contest_key>/mcq/<int:mcq_id>/content/', views.HPEMCQContentView.as_view(), name='hpe_mcq_content'),
    path('contest/<str:contest_key>/mcq/<int:mcq_id>/submit/', views.HPEMCQSubmitView.as_view(), name='hpe_mcq_submit'),
    # Contest Join/Leave
    path('contest/<str:contest_key>/join/', views.HPEContestJoinView.as_view(), name='hpe_contest_join'),
    path('contest/<str:contest_key>/leave/', views.HPEContestLeaveView.as_view(), name='hpe_contest_leave'),
    # Get all submissions for Proctor backend
    path('contest/<str:contest_key>/submissions/', views.HPEContestSubmissionsView.as_view(), name='hpe_contest_submissions'),
]

