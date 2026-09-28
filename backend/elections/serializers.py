from rest_framework import serializers

from .models import Ballot, Candidate, Election
from .services import normalize_rankings


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ["id", "code", "name"]


class BallotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ballot
        fields = ["id", "synthetic_ballot_id", "raw_rankings", "normalized_rankings"]
        read_only_fields = ["normalized_rankings"]


class ElectionSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True)
    ballots = BallotSerializer(many=True)

    class Meta:
        model = Election
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "candidates",
            "ballots",
            "rule_duplicate_rankings",
            "rule_unranked_candidates",
            "rule_invalid_candidates",
            "rule_tie_break",
        ]
        read_only_fields = ["created_at"]

    def validate(self, attrs):
        candidates = attrs.get("candidates", [])
        ballots = attrs.get("ballots", [])

        if len(candidates) < 2:
            raise serializers.ValidationError("至少需要两名候选人。")

        codes = [candidate["code"] for candidate in candidates]
        if len(codes) != len(set(codes)):
            raise serializers.ValidationError("候选人代码必须唯一。")

        valid_codes = set(codes)
        ballot_numbers = [ballot["synthetic_ballot_id"] for ballot in ballots]
        if len(ballot_numbers) != len(set(ballot_numbers)):
            raise serializers.ValidationError("合成选票编号必须唯一。")

        for ballot in ballots:
            if not isinstance(ballot.get("raw_rankings"), list):
                raise serializers.ValidationError(
                    {f"ballot {ballot.get('synthetic_ballot_id')}": "raw_rankings 必须是候选人代码数组。"}
                )
            normalized, _warnings = normalize_rankings(ballot["raw_rankings"], valid_codes)
            ballot["normalized_rankings"] = normalized

        return attrs

    def create(self, validated_data):
        candidates_data = validated_data.pop("candidates")
        ballots_data = validated_data.pop("ballots")
        election = Election.objects.create(**validated_data)

        Candidate.objects.bulk_create(
            [Candidate(election=election, **candidate) for candidate in candidates_data]
        )
        Ballot.objects.bulk_create(
            [
                Ballot(
                    election=election,
                    synthetic_ballot_id=ballot["synthetic_ballot_id"],
                    raw_rankings=ballot["raw_rankings"],
                    normalized_rankings=ballot["normalized_rankings"],
                )
                for ballot in ballots_data
            ]
        )
        return election
