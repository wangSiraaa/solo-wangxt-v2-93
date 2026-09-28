"""写入两个匿名合成选举样例（幂等：同名规则/选举存在则跳过）。"""
from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import Ballot, Candidate, Election, RuleSet
from elections.services.ballot_cleaning import normalize_preferences

SYNTHETIC = "匿名合成数据，仅用于计票流程演示，不代表任何真实选举"


# 样例一：首轮无人过半、连续多轮转移、末轮含穷尽票，且出现最低票并列决胜。
# 每条记录为一张合成票（weight=1），共 20 张。
ELECTION_ONE = {
    "name": "样例一：连续转移与穷尽票（4 候选人 / 20 张合成票）",
    "candidates": [
        ("A", "甲", 1),
        ("B", "乙", 2),
        ("C", "丙", 3),
        ("D", "丁", 4),
    ],
    # (原始偏好序列, 票数)。刻意混入重复排名与无效代码。
    "ballot_groups": [
        (["A", "B"], 5),
        (["A", "C"], 2),
        (["B", "A"], 5),
        (["B", "D", "C"], 2),
        (["C", "B", "A"], 2),
        (["C", "C", "D"], 1),          # 重复 C：保留首次
        (["D", "X", "A"], 1),          # X 无效：剔除
        (["D"], 1),
        (["D", "C", "B"], 1),
    ],
}

# 样例二：含未排名/重复/无效/空白票的清洗演示；末轮严格过半当选。
# 共 15 张合成票，其中 3 张清洗后无效。
ELECTION_TWO = {
    "name": "样例二：规则清洗与过半当选（3 候选人 / 15 张合成票，3 张无效）",
    "candidates": [
        ("X", "梅花", 1),
        ("Y", "兰花", 2),
        ("Z", "竹子", 3),
    ],
    "ballot_groups": [
        (["X"], 4),
        (["Y", "Z"], 3),
        (["Z", "Y", "X"], 1),
        (["Z", "X"], 1),
        (["Z", "Z"], 1),               # 重复 Z：保留首次
        (["Q", "Z"], 1),               # Q 无效：降级为 [Z]
        (["Y"], 1),
        ([], 2),                        # 空白：无效票
        (["Q"], 1),                     # 只有无效代码：无效票
    ],
}


class Command(BaseCommand):
    help = "写入匿名合成的 IRV 演示数据（幂等）"

    @transaction.atomic
    def handle(self, *args, **options):
        ruleset, _ = RuleSet.objects.get_or_create(
            name="标准 IRV 规则（严格过半 / 代码序决胜 / 穷尽票计分母）",
            defaults={
                "description": (
                    "重复排名保留首次；无效候选人代码剔除；"
                    "未排名候选人在其所偏好候选全部淘汰后令选票穷尽；"
                    "严格过半（含穷尽票分母）；同票按候选人代码升序先淘汰。"
                ),
            },
        )

        for spec in (ELECTION_ONE, ELECTION_TWO):
            if Election.objects.filter(name=spec["name"]).exists():
                self.stdout.write(f"跳过（已存在）：{spec['name']}")
                continue
            election = Election.objects.create(
                name=spec["name"], ruleset=ruleset, seat_count=1,
                note=SYNTHETIC,
            )
            valid_codes = {code for code, _, _ in spec["candidates"]}
            for code, cname, order in spec["candidates"]:
                Candidate.objects.create(
                    election=election, code=code, name=cname,
                    display_order=order,
                )
            for raw, count in spec["ballot_groups"]:
                cleaned, is_valid, reason = normalize_preferences(
                    raw, valid_codes
                )
                for _ in range(count):
                    Ballot.objects.create(
                        election=election,
                        preferences_raw=raw,
                        preferences=cleaned,
                        weight=1,
                        is_valid=is_valid,
                        invalid_reason=reason,
                    )
            self.stdout.write(self.style.SUCCESS(
                f"已写入：{spec['name']}"
            ))
