from rest_framework import serializers

from .models import Ballot, Candidate, Election, RuleSet


class RuleSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleSet
        fields = [
            "id", "name", "duplicate_rank_handling",
            "invalid_candidate_handling", "unranked_handling",
            "majority_rule", "tie_break", "description",
        ]


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ["id", "code", "name", "display_order"]


class BallotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ballot
        fields = [
            "id", "preferences_raw", "preferences", "weight",
            "is_valid", "invalid_reason",
        ]


class ElectionListSerializer(serializers.ModelSerializer):
    ruleset = RuleSetSerializer(read_only=True)
    candidate_count = serializers.IntegerField(read_only=True)
    ballot_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Election
        fields = [
            "id", "name", "seat_count", "ruleset", "note",
            "created_at", "candidate_count", "ballot_count",
        ]


class RoundTallyRowSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    votes = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()


class TransferSerializer(serializers.Serializer):
    from_code = serializers.CharField()
    from_name = serializers.CharField()
    to_code = serializers.CharField(allow_null=True)
    to_name = serializers.CharField()
    votes = serializers.IntegerField()


class RoundSerializer(serializers.Serializer):
    round_number = serializers.IntegerField()
    transfers_in = TransferSerializer(many=True)
    exhausted_delta = serializers.IntegerField()
    tally_rows = RoundTallyRowSerializer(many=True)
    active_ballots = serializers.IntegerField()
    exhausted_ballots = serializers.IntegerField()
    counted_ballots = serializers.IntegerField()
    majority_threshold = serializers.IntegerField()
    min_votes = serializers.IntegerField(allow_null=True)
    tied_min_codes = serializers.ListField(child=serializers.CharField())
    eliminated_codes = serializers.ListField(child=serializers.CharField())
    eliminated_name = serializers.CharField(allow_null=True)
    elected_code = serializers.CharField(allow_null=True)
    elected_name = serializers.CharField(allow_null=True)
    terminal_reason = serializers.CharField(allow_null=True)


class ResultSerializer(serializers.Serializer):
    rounds = RoundSerializer(many=True)
    winner_code = serializers.CharField(allow_null=True)
    winner_name = serializers.CharField(allow_null=True)
    terminated_reason = serializers.CharField(allow_null=True)
    total_valid_weight = serializers.IntegerField()
    tie_break_order = serializers.ListField(child=serializers.CharField())
    conservation_ok = serializers.BooleanField()
    invalid_ballots = serializers.IntegerField()
    total_ballots = serializers.IntegerField()
