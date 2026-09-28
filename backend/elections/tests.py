from django.test import TestCase

from .models import Ballot, Candidate, Election
from .services import normalize_rankings, tally_irv


def create_election(candidates, raw_ballots):
    election = Election.objects.create(title="测试选举")
    code_to_candidate = {}
    for code, name in candidates:
        code_to_candidate[code] = Candidate.objects.create(
            election=election, code=code, name=name
        )
    valid_codes = set(code_to_candidate)
    for number, raw in enumerate(raw_ballots, start=1):
        normalized, _ = normalize_rankings(raw, valid_codes)
        Ballot.objects.create(
            election=election,
            synthetic_ballot_id=number,
            raw_rankings=raw,
            normalized_rankings=normalized,
        )
    return election


class NormalizationTests(TestCase):
    def test_invalid_and_duplicate_rankings_are_ignored(self):
        normalized, warnings = normalize_rankings(["A", "X", "A", "B"], {"A", "B"})
        self.assertEqual(normalized, ["A", "B"])
        self.assertEqual([item.reason for item in warnings], ["无效或不属于本次选举的候选人代码，已忽略", "同一候选人重复排名，只保留第一次出现的最高偏好，后续重复项已忽略"])


class TallyConservationTests(TestCase):
    def setUp(self):
        self.election = create_election(
            [("A", "林安"), ("B", "陈北"), ("C", "王晨"), ("D", "赵东"), ("E", "何方")],
            [
                ["A", "B", "C"],
                ["A", "B", "C"],
                ["A", "B", "C"],
                ["A", "B", "D", "A"],
                ["A", "B", "D"],
                ["B", "A", "E"],
                ["B", "A", "E"],
                ["B", "A"],
                ["B", "A"],
                ["B", "E", "A"],
                ["B", "E", "A"],
                ["C", "A", "B"],
                ["C", "A", "B"],
                ["C", "A", "B"],
                ["C", "E", "A"],
                ["D", "B"],
                ["D", "B"],
                ["D", "A"],
                ["D"],
                ["E", "B", "A"],
                ["E", "B", "A"],
                ["E", "B", "A"],
                ["E", "X"],
                ["Z"],
                [],
            ],
        )

    def test_sample_first_round_no_majority_continuous_transfers_and_winner(self):
        result = tally_irv(self.election)
        rounds = result["rounds"]

        self.assertEqual(4, len(rounds))
        self.assertEqual(["C", "D", "E", None], [item["eliminated_code"] for item in rounds])
        self.assertIsNone(rounds[0]["winner_code"])
        self.assertEqual("B", result["winner_code"])

        first = rounds[0]
        first_votes = {item["code"]: item["votes"] for item in first["candidate_results"]}
        self.assertEqual({"A": 5, "B": 6, "C": 4, "D": 4, "E": 4}, first_votes)
        self.assertEqual(23, first["valid_total"])
        self.assertEqual(2, first["exhausted_total"])
        self.assertEqual(12, first["majority_threshold"])

        second, third, fourth = rounds[1:]
        self.assertEqual(23, second["valid_total"])
        self.assertEqual(2, second["exhausted_total"])
        self.assertEqual(22, third["valid_total"])
        self.assertEqual(3, third["exhausted_total"])
        self.assertEqual(21, fourth["valid_total"])
        self.assertEqual(4, fourth["exhausted_total"])

        final_votes = {item["code"]: item["votes"] for item in fourth["candidate_results"] if item["active"]}
        self.assertEqual({"A": 10, "B": 11}, final_votes)
        self.assertEqual(11, fourth["majority_threshold"])

        self.assertEqual(
            [
                [("C", "A", 3), ("C", "E", 1)],
                [("D", "A", 1), ("D", "B", 2), ("D", None, 1)],
                [("E", "A", 1), ("E", "B", 3), ("E", None, 1)],
            ],
            [
                [
                    (item["source_code"], item["destination_code"], item["count"])
                    for item in round_record["transfers"]
                ]
                for round_record in rounds[1:]
            ],
        )

        for index, round_record in enumerate(rounds):
            candidate_votes = sum(
                candidate["votes"] for candidate in round_record["candidate_results"] if candidate["active"]
            )
            self.assertEqual(candidate_votes, round_record["valid_total"])
            self.assertEqual(
                round_record["valid_total"] + round_record["exhausted_total"],
                round_record["total_ballots"],
            )

            if index == 0:
                self.assertEqual([], round_record["transfers"])
            else:
                previous_round = rounds[index - 1]
                eliminated_previous = next(
                    candidate
                    for candidate in previous_round["candidate_results"]
                    if candidate["code"] == previous_round["eliminated_code"]
                )
                transferred = sum(item["count"] for item in round_record["transfers"])
                self.assertEqual(transferred, eliminated_previous["votes"])

    def test_all_empty_ballots_are_exhausted_from_first_round(self):
        election = create_election(
            [("A", "甲"), ("B", "乙")],
            [[], ["X"], ["A", "A", "X", "B"]],
        )

        result = tally_irv(election)
        first_round = result["rounds"][0]

        self.assertEqual(1, first_round["valid_total"])
        self.assertEqual(2, first_round["exhausted_total"])
        self.assertEqual([1, 2], first_round["exhausted_ballot_ids"])
        self.assertEqual(1, first_round["majority_threshold"])
        self.assertEqual("A", result["winner_code"])

    def test_tie_break_uses_configured_code_order_without_randomness(self):
        # A and B tie at the bottom. Candidate code A is lexicographically
        # earlier and is eliminated; both repeated runs must be identical.
        election = create_election(
            [("A", "甲"), ("B", "乙"), ("C", "丙")],
            [["A"], ["B"], ["C", "A"], ["C", "B"]],
        )
        first_result = tally_irv(election)
        second_result = tally_irv(election)
        self.assertEqual("A", first_result["rounds"][0]["eliminated_code"])
        self.assertTrue(first_result["rounds"][0]["tie_break_applied"])
        self.assertEqual(first_result, second_result)
