from django.urls import path

from . import views

urlpatterns = [
    path("elections/", views.ElectionListView.as_view()),
    path("elections/<int:pk>/", views.ElectionDetailView.as_view()),
    path(
        "elections/<int:election_pk>/candidates/",
        views.CandidateListView.as_view(),
    ),
    path(
        "elections/<int:election_pk>/ballots/",
        views.BallotListView.as_view(),
    ),
    path(
        "elections/<int:election_pk>/result/",
        views.ResultView.as_view(),
    ),
]
