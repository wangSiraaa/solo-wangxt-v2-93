from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import Ballot, Candidate, Election
from elections.services import normalize_rankings


CANDIDATES = [
    {"code": "A", "name": "林安"},
    {"code": "B", "name": "陈北"},
    {"code": "C", "name": "王晨"},
    {"code": "D", "name": "赵东"},
    {"code": "E", "name": "何方"},
]

RAW_BALLOTS = [
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
]


class Command(BaseCommand):
    help = "Create the deterministic synthetic IRV demonstration election."

    @transaction.atomic
    def handle(self, *args, **options):
        election, created = Election.objects.get_or_create(
            title="社团联合会单席位排序选择投票演示",
            defaults={
                "description": "匿名合成选票；用于展示无过半、连续转移和穷尽票，不对应真实选举。",
            },
        )
        if not created:
            self.stdout.write(f"演示选举已存在：election_id={election.id}")
            return

        candidate_map = {}
        for item in CANDIDATES:
            candidate = Candidate.objects.create(election=election, **item)
            candidate_map[candidate.code] = candidate

        valid_codes = set(candidate_map)
        for number, raw in enumerate(RAW_BALLOTS, start=1):
            normalized, _warnings = normalize_rankings(raw, valid_codes)
            Ballot.objects.create(
                election=election,
                synthetic_ballot_id=number,
                raw_rankings=raw,
                normalized_rankings=normalized,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"已创建演示选举 election_id={election.id}，候选人数 {len(CANDIDATES)}，选票数 {len(RAW_BALLOTS)}。"
            )
        )
