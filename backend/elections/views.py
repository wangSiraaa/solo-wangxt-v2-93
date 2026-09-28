from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ballot, Election
from .serializers import ElectionSerializer
from .services import tally_irv


class ElectionListCreateView(generics.ListCreateAPIView):
    queryset = Election.objects.prefetch_related(
        "candidates",
        Prefetch("ballots", queryset=Ballot.objects.order_by("synthetic_ballot_id")),
    ).all()
    serializer_class = ElectionSerializer


class ElectionDetailView(generics.RetrieveAPIView):
    queryset = Election.objects.prefetch_related(
        "candidates",
        Prefetch("ballots", queryset=Ballot.objects.order_by("synthetic_ballot_id")),
    ).all()
    serializer_class = ElectionSerializer


class ElectionTallyView(APIView):
    def get(self, request, pk):
        election = Election.objects.prefetch_related(
            "candidates",
            Prefetch("ballots", queryset=Ballot.objects.order_by("synthetic_ballot_id")),
        ).get(pk=pk)
        tally = tally_irv(election)
        return Response(
            {
                "election": ElectionSerializer(election).data,
                "rules": {
                    "duplicate_rankings": election.rule_duplicate_rankings,
                    "unranked_candidates": election.rule_unranked_candidates,
                    "invalid_candidates": election.rule_invalid_candidates,
                    "tie_break": election.rule_tie_break,
                },
                **tally,
            }
        )
