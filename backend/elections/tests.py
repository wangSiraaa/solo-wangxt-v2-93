from django.test import TestCase
from rest_framework.test import APIClient

from elections.services.ballot_cleaning import normalize_preferences
from elections.services.tabulation import run_irv

CODES = {"A", "B", "C", "D"}


class BallotCleaningTests(TestCase):
    def test_duplicate_keeps_first(self):
        cleaned, valid, reason = normalize_preferences(
            ["C", "C", "D"], CODES
        )
        self.assertTrue(valid)
        self.assertEqual(cleaned, ["C", "D"])
        self.assertIn("重复", reason)

    def test_invalid_code_dropped_but_ballot_lives(self):
        cleaned, valid, reason = normalize_preferences(
            ["D", "X", "A"], CODES
        )
        self.assertTrue(valid)
        self.assertEqual(cleaned, ["D", "A"])
        self.assertIn("X", reason)

    def test_empty_is_invalid(self):
        for raw in ([], None, ["Q"], ["", "  "]):
            cleaned, valid, _ = normalize_preferences(raw, CODES)
            self.assertFalse(valid)
            self.assertEqual(cleaned, [])

    def test_non_list_is_invalid(self):
        _, valid, reason = normalize_preferences("A>B", CODES)
        self.assertFalse(valid)
        self.assertIn("不是排名序列", reason)


class TabulationConservationTests(TestCase):
    def run_and_check(self, candidates, ballots, total):
        result = run_irv(candidates, ballots)
        self.assertTrue(result["conservation_ok"])
        self.assertEqual(result["total_valid_weight"], total)
        for rnd in result["rounds"]:
            on_hand = sum(
                row["votes"] for row in rnd["tally_rows"]
                if row["votes"] is not None
            )
            # 守恒：各候选人票数 + 穷尽票 = 有效票总数
            self.assertEqual(
                on_hand + rnd["exhausted_ballots"], total
            )
            self.assertEqual(
                rnd["counted_ballots"],
                rnd["active_ballots"] + rnd["exhausted_ballots"],
            )
        return result

    def test_conservation_with_exhaustion(self):
        candidates = [
            {"code": "A", "name": "甲"},
            {"code": "B", "name": "乙"},
        ]
        ballots = [
            {"preferences": ["A"], "weight": 3},
            {"preferences": ["B"], "weight": 1},
        ]
        result = self.run_and_check(candidates, ballots, 4)
        self.assertEqual(result["winner_code"], "A")
        self.assertEqual(result["rounds"][0]["majority_threshold"], 3)

    def test_exhausted_ballots_stay_in_majority_denominator(self):
        # 5 张有效票：3 张只投 A，2 张投给首轮被淘汰者后穷尽。
        candidates = [
            {"code": "A", "name": "甲"},
            {"code": "B", "name": "乙"},
            {"code": "C", "name": "丙"},
        ]
        ballots = [
            {"preferences": ["A"], "weight": 3},
            {"preferences": ["C"], "weight": 2},
        ]
        result = run_irv(candidates, ballots)
        last = result["rounds"][-1]
        # 分母始终是 5，门槛 3；A 以 3/5 严格过半，而非因 2 票穷尽改变门槛。
        self.assertEqual(last["majority_threshold"], 3)
        self.assertEqual(result["winner_code"], "A")

    def test_acclamation_when_majority_never_reachable(self):
        # 5 张票：A2、B1、C2（C 被淘汰后票穷尽）；剩两人时各 2 票，
        # 穷尽票 2 令过半门槛始终为 3，无人能过半，最后一人按规则当选。
        candidates = [
            {"code": "A", "name": "甲"},
            {"code": "B", "name": "乙"},
            {"code": "C", "name": "丙"},
        ]
        ballots = [
            {"preferences": ["A"], "weight": 2},
            {"preferences": ["B"], "weight": 1},
            {"preferences": ["C"], "weight": 2},
        ]
        result = self.run_and_check(candidates, ballots, 5)
        # R1 最低 B=1 淘汰；R2 A=2 C=2 同票，代码序淘汰 A；C 末轮剩一人。
        self.assertEqual(result["winner_code"], "C")
        self.assertEqual(
            result["terminated_reason"], "acclamation_last_standing"
        )
        last = result["rounds"][-1]
        self.assertEqual(last["majority_threshold"], 3)
        self.assertEqual(last["exhausted_ballots"], 3)

    def test_no_valid_ballots(self):
        result = run_irv(
            [{"code": "A", "name": "甲"}], []
        )
        self.assertIsNone(result["winner_code"])
        self.assertEqual(result["terminated_reason"], "no_valid_ballots")


class TieBreakTests(TestCase):
    BALLOTS = [
        {"preferences": ["B", "C"], "weight": 2},
        {"preferences": ["C", "B"], "weight": 2},
        {"preferences": ["A"], "weight": 1},
    ]

    def test_code_ascending_eliminated_first(self):
        candidates = [
            {"code": "A", "name": "甲"},
            {"code": "B", "name": "乙"},
            {"code": "C", "name": "丙"},
        ]
        result = run_irv(candidates, self.BALLOTS)
        r1 = result["rounds"][0]
        self.assertEqual(r1["tied_min_codes"], ["A"])
        self.assertEqual(r1["eliminated_codes"], ["A"])
        # A 票穷尽，B、C 各 2，再次同票：按代码序淘汰 B，C 末轮当选。
        r2 = result["rounds"][1]
        self.assertEqual(r2["eliminated_codes"], ["B"])
        self.assertEqual(result["winner_code"], "C")

    def test_renaming_codes_changes_winner(self):
        # 得票结构完全对称（两个阵营各 2 张、彼此交叉背书，另有 1 张孤立票），
        # 仅改变同票阵营所持代码，胜者就按代码序确定地改变：
        # 孤立票为代码 A 时，B/C 同票 -> 先淘汰 B -> C 胜；
        # 孤立票为代码 C 时，A/B 同票 -> 先淘汰 A -> B 胜。
        candidates = [
            {"code": "A", "name": "甲"},
            {"code": "B", "name": "乙"},
            {"code": "C", "name": "丙"},
        ]
        mirrored = [
            {"preferences": ["A", "B"], "weight": 2},
            {"preferences": ["B", "A"], "weight": 2},
            {"preferences": ["C"], "weight": 1},
        ]
        result_a = run_irv(candidates, self.BALLOTS)
        result_b = run_irv(candidates, mirrored)
        self.assertEqual(result_a["winner_code"], "C")
        self.assertEqual(result_b["winner_code"], "B")

    def test_deterministic_repeated_runs(self):
        candidates = [
            {"code": "A", "name": "甲"},
            {"code": "B", "name": "乙"},
            {"code": "C", "name": "丙"},
        ]
        first = run_irv(candidates, self.BALLOTS)
        for _ in range(5):
            again = run_irv(candidates, self.BALLOTS)
            self.assertEqual(
                [r["eliminated_codes"] for r in again["rounds"]],
                [r["eliminated_codes"] for r in first["rounds"]],
            )


class APITests(TestCase):
    fixtures_loaded = False

    @classmethod
    def setUpTestData(cls):
        from elections.management.commands.seed_demo import (
            ELECTION_ONE, ELECTION_TWO, SYNTHETIC,
        )
        from elections.models import (
            Ballot, Candidate, Election, RuleSet,
        )
        from elections.services.ballot_cleaning import normalize_preferences

        ruleset = RuleSet.objects.create(
            name="测试规则",
            tie_break="code_asc",
        )
        cls.ids = []
        for spec in (ELECTION_ONE, ELECTION_TWO):
            e = Election.objects.create(
                name=spec["name"], ruleset=ruleset, note=SYNTHETIC
            )
            codes = {c[0] for c in spec["candidates"]}
            for code, cname, order in spec["candidates"]:
                Candidate.objects.create(
                    election=e, code=code, name=cname,
                    display_order=order,
                )
            for raw, count in spec["ballot_groups"]:
                cleaned, valid, reason = normalize_preferences(raw, codes)
                for _ in range(count):
                    Ballot.objects.create(
                        election=e, preferences_raw=raw,
                        preferences=cleaned, weight=1,
                        is_valid=valid, invalid_reason=reason,
                    )
            cls.ids.append(e.id)

    def test_election_list(self):
        resp = APIClient().get("/api/elections/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_result_sample_one(self):
        resp = APIClient().get(f"/api/elections/{self.ids[0]}/result/")
        data = resp.json()
        self.assertTrue(data["conservation_ok"])
        self.assertEqual(data["winner_code"], "B")
        self.assertEqual(data["total_valid_weight"], 20)
        self.assertEqual(len(data["rounds"]), 4)
        r1 = data["rounds"][0]
        self.assertEqual(r1["tied_min_codes"], ["C", "D"])
        # 末轮 B=15、穷尽=5，门槛 11，严格过半。
        last = data["rounds"][-1]
        b_row = next(r for r in last["tally_rows"] if r["code"] == "B")
        self.assertEqual(b_row["votes"], 15)
        self.assertEqual(last["exhausted_ballots"], 5)
        self.assertEqual(last["majority_threshold"], 11)

    def test_result_sample_two_invalid_count(self):
        resp = APIClient().get(f"/api/elections/{self.ids[1]}/result/")
        data = resp.json()
        self.assertEqual(data["invalid_ballots"], 3)
        self.assertEqual(data["total_valid_weight"], 12)
        self.assertEqual(data["winner_code"], "Z")
