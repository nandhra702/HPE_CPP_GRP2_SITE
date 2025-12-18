from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.HPEContestLoginView.as_view(), name='hpe_contest_login'),
    path('contest/<str:contest_key>/', views.HPEContestView.as_view(), name='hpe_contest_view'),
]
