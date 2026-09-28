from django.db.models import Count, Sum
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Ballot, Candidate, Election
from .serializers import (
    BallotSerializer,
    CandidateSerializer,
    ElectionListSerializer,
    ResultSerializer,
)
from .services.tabulation import run_irv


class ElectionListView(ListAPIView):
    serializer_class = ElectionListSerializer

    def get_queryset(self):
        return (
            Election.objects.select_related("ruleset")
            .annotate(
                candidate_count=Count("candidates", distinct=True),
                ballot_count=Count("ballots", distinct=True),
            )
            .order_by("id")
        )


class ElectionDetailView(RetrieveAPIView):
    serializer_class = ElectionListSerializer
    queryset = Election.objects.select_related("ruleset").all()


class CandidateListView(ListAPIView):
    serializer_class = CandidateSerializer

    def get_queryset(self):
        return Candidate.objects.filter(
            election_id=self.kwargs["election_pk"]
        ).order_by("display_order", "code")


class BallotListView(ListAPIView):
    """匿名合成选票（分页，仅含偏好与票重，无任何选民信息）。"""

    serializer_class = BallotSerializer
    pagination_class = None

    def get_queryset(self):
        return Ballot.objects.filter(
            election_id=self.kwargs["election_pk"]
        ).order_by("id")


class ResultView(APIView):
    """逐轮 IRV 计票结果（无缓存、无随机；每次按库内数据重算）。"""

    def get(self, request, election_pk: int):
        election = Election.objects.select_related("ruleset").get(
            pk=election_pk
        )
        candidates = list(
            Candidate.objects.filter(election=election).values(
                "code", "name"
            )
        )
        valid_ballots = Ballot.objects.filter(
            election=election, is_valid=True
        ).values("preferences", "weight")
        invalid_weight = (
            Ballot.objects.filter(election=election, is_valid=False)
            .aggregate(total=Sum("weight"))["total"]
        ) or 0

        result = run_irv(
            candidates=list(candidates),
            ballots=list(valid_ballots),
            tie_break=election.ruleset.tie_break,
        )
        result["invalid_ballots"] = invalid_weight
        result["total_ballots"] = (
            result["total_valid_weight"] + invalid_weight
        )
        return Response(ResultSerializer(result).data)
