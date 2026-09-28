"""IRV（Instant-Runoff Voting，单席位排序复选）计票引擎。

输入全部来自 PostgreSQL 中已清洗的匿名合成选票；本模块无随机数、
无时间相关逻辑，同一份数据永远得到同一份逐轮结果。

过半口径：严格过半，分母为“有效票总数”，每轮都包含已穷尽票
（votes > counted // 2）。同票时按候选人 code 字典序决胜，
先淘汰 code 较小者；全程不做任何随机选择。
"""
from __future__ import annotations

from typing import Iterable

EXHAUSTED = "__exhausted__"


def _current_pick(prefs: list[str], eliminated: set[str]) -> str | None:
    """该选票在本轮流向的候选人：第一个尚未被淘汰的偏好；没有则穷尽。"""
    for code in prefs:
        if code not in eliminated:
            return code
    return None


def run_irv(
    candidates: list[dict],
    ballots: Iterable[dict],
    *,
    tie_break: str = "code_asc",
) -> dict:
    """执行逐轮 IRV 计票。

    candidates: [{"code": "A", "name": "..."}]
    ballots:    [{"preferences": ["A", "C"], "weight": 3}, ...]
                 只传 is_valid=True 的选票。

    返回结构见 README「计票结果 JSON」。
    """
    if tie_break != "code_asc":
        raise ValueError(f"不支持的决胜方式: {tie_break}")

    names = {c["code"]: c["name"] for c in candidates}
    all_codes = sorted(names)  # 决胜次序：code 字典序（事先固定）
    ballot_list = [
        (list(b["preferences"]), int(b["weight"]))
        for b in ballots
        if b.get("preferences")
    ]
    # 防御：选票只可能引用本次候选人代码（入库前已清洗）。
    for prefs, _ in ballot_list:
        unknown = [code for code in prefs if code not in names]
        if unknown:
            raise ValueError(f"选票出现未知候选人代码: {unknown}")
    total_weight = sum(w for _, w in ballot_list)

    rounds: list[dict] = []
    eliminated: set[str] = set()
    standing = set(all_codes)

    # 待挂到“下一轮”的转移流（上一轮淘汰造成的）。
    pending_transfers: list[dict] = []
    pending_exhausted_delta = 0

    if total_weight == 0 or not all_codes:
        return {
            "rounds": [],
            "winner_code": None,
            "winner_name": None,
            "terminated_reason": (
                "no_candidates" if not all_codes else "no_valid_ballots"
            ),
            "total_valid_weight": total_weight,
            "tie_break_order": all_codes,
            "conservation_ok": True,
        }

    while True:
        round_no = len(rounds) + 1

        # 1) 本轮分票：每一张有效票流向其最高且尚未淘汰的偏好。
        tally = {code: 0 for code in standing}
        exhausted_weight = 0
        # 记录被淘汰者持有的票，供构造转移说明。
        holders: dict[str, list[tuple[list[str], int]]] = {}
        for prefs, weight in ballot_list:
            pick = _current_pick(prefs, eliminated)
            if pick is None:
                exhausted_weight += weight
            else:
                tally[pick] += weight
                holders.setdefault(pick, []).append((prefs, weight))

        active_weight = total_weight - exhausted_weight
        counted = active_weight + exhausted_weight
        threshold = counted // 2 + 1

        # 票数守恒断言：候选人票数之和 + 穷尽票 = 有效票总数。
        assert sum(tally.values()) + exhausted_weight == total_weight, (
            f"第 {round_no} 轮票数不守恒"
        )

        row_map = {}
        for code in all_codes:
            if code in standing:
                row_map[code] = {
                    "code": code, "name": names[code],
                    "votes": tally[code],
                    "status": "standing",
                }
            else:
                row_map[code] = {
                    "code": code, "name": names[code],
                    "votes": None,
                    "status": "eliminated",
                }

        winners = sorted(
            c for c in standing if tally[c] >= threshold
        )
        # 单席位：严格过半即当选（threshold 已是 floor(n/2)+1）。
        elected = winners[0] if winners else None

        # 无人过半但只剩一人：其因其余候选人均被淘汰而当选。
        acclamation = elected is None and len(standing) == 1
        if acclamation:
            elected = sorted(standing)[0]
            row_map[elected]["status"] = "elected"

        if elected is not None:
            rounds.append({
                "round_number": round_no,
                "transfers_in": pending_transfers,
                "exhausted_delta": pending_exhausted_delta,
                "tally_rows": [row_map[c] for c in all_codes],
                "active_ballots": active_weight,
                "exhausted_ballots": exhausted_weight,
                "counted_ballots": counted,
                "majority_threshold": threshold,
                "min_votes": None,
                "tied_min_codes": [],
                "eliminated_codes": [],
                "elected_code": elected,
                "elected_name": names[elected],
                "terminal_reason": (
                    "acclamation_last_standing"
                    if acclamation else "majority"
                ),
            })
            break

        # 2) 无人过半：找出本轮最低票。
        min_votes = min(tally.values())
        tied_min = sorted(c for c in standing if tally[c] == min_votes)
        # 同票决胜：code 字典序最靠前者淘汰（事先配置，禁止随机）。
        drop = tied_min[0]

        # 3) 计算被淘汰者手中选票的下一有效偏好（构造转移流）。
        flows: dict[str, int] = {}
        exhausted_delta = 0
        for prefs, weight in holders.get(drop, []):
            nxt = _current_pick(prefs, eliminated | {drop})
            key = nxt if nxt is not None else EXHAUSTED
            flows[key] = flows.get(key, 0) + weight
            if nxt is None:
                exhausted_delta += weight

        transferred_out = sum(flows.values())
        assert transferred_out == tally[drop], (
            f"第 {round_no} 轮转移量不等于被淘汰者票数"
        )

        transfers = [
            {
                "from_code": drop,
                "from_name": names[drop],
                "to_code": None if key == EXHAUSTED else key,
                "to_name": (
                    "穷尽（无下一有效偏好）"
                    if key == EXHAUSTED else names[key]
                ),
                "votes": votes,
            }
            for key, votes in sorted(
                flows.items(),
                key=lambda kv: (kv[0] == EXHAUSTED, kv[0]),
            )
        ]

        rounds.append({
            "round_number": round_no,
            "transfers_in": pending_transfers,
            "exhausted_delta": pending_exhausted_delta,
            "tally_rows": [row_map[c] for c in all_codes],
            "active_ballots": active_weight,
            "exhausted_ballots": exhausted_weight,
            "counted_ballots": counted,
            "majority_threshold": threshold,
            "min_votes": min_votes,
            "tied_min_codes": tied_min,
            "eliminated_codes": [drop],
            "eliminated_name": names[drop],
            "elected_code": None,
            "elected_name": None,
            "terminal_reason": None,
        })

        eliminated.add(drop)
        standing.remove(drop)
        pending_transfers = transfers
        pending_exhausted_delta = exhausted_delta

    return {
        "rounds": rounds,
        "winner_code": elected,
        "winner_name": names[elected],
        "terminated_reason": rounds[-1]["terminal_reason"],
        "total_valid_weight": total_weight,
        "tie_break_order": all_codes,
        "conservation_ok": all(
            sum(
                row["votes"] for row in rnd["tally_rows"]
                if row["votes"] is not None
            ) + rnd["exhausted_ballots"] == total_weight
            for rnd in rounds
        ),
    }
