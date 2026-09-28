from rest_framework.test import APITestCase


class ElectionTallyApiTests(APITestCase):
    def payload_from_demo_fixture(self):
        return {
            "title": "通过 API 创建的合成演示",
            "description": "API 校验测试",
            "candidates": [
                {"code": "A", "name": "甲"},
                {"code": "B", "name": "乙"},
            ],
            "ballots": [
                {"synthetic_ballot_id": 1, "raw_rankings": ["A", "A", "X", "B"]},
                {"synthetic_ballot_id": 2, "raw_rankings": []},
            ],
        }

    def test_create_election_normalizes_ballots(self):
        response = self.client.post(
            "/api/elections/",
            data=self.payload_from_demo_fixture(),
            format="json",
        )

        self.assertEqual(201, response.status_code, response.content)
        data = response.json()
        self.assertEqual(["A", "B"], data["ballots"][0]["normalized_rankings"])
        self.assertEqual([], data["ballots"][1]["normalized_rankings"])

    def test_tally_endpoint_returns_rounds_rules_and_conservation_fields(self):
        from elections.management.commands.seed_demo import Command

        Command().handle()
        election_id = self._first_demo_election_id()
        response = self.client.get(f"/api/elections/{election_id}/tally/")

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual("B", data["winner_code"])
        self.assertEqual(25, data["total_ballots"])
        self.assertEqual(4, len(data["rounds"]))
        self.assertIn("duplicate_rankings", data["rules"])
        first_round = data["rounds"][0]
        self.assertEqual(23, first_round["valid_total"])
        self.assertEqual(2, first_round["exhausted_total"])
        self.assertEqual([24, 25], first_round["exhausted_ballot_ids"])
        self.assertTrue(first_round["tie_break_applied"])

    def _first_demo_election_id(self):
        from elections.models import Election

        return Election.objects.values_list("id", flat=True).first()
