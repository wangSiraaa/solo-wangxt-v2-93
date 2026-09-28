from django.urls import path

from .views import ElectionDetailView, ElectionListCreateView, ElectionTallyView

urlpatterns = [
    path("elections/", ElectionListCreateView.as_view(), name="election-list"),
    path("elections/<int:pk>/", ElectionDetailView.as_view(), name="election-detail"),
    path("elections/<int:pk>/tally/", ElectionTallyView.as_view(), name="election-tally"),
]
