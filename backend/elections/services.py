from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationWarning:
    ballot_id: int
    code: str | None
    reason: str
    position: int | None = None


def normalize_rankings(raw_rankings, valid_codes):
    """Return normalized preferences and deterministic normalization warnings.

    A ranking must be an ordered list of candidate codes. Invalid codes are
    ignored. For duplicate occurrences of the same candidate, only the first
    (highest) occurrence is retained.
    """
    normalized = []
    warnings = []
    seen = set()

    if not isinstance(raw_rankings, list):
        return normalized, [
            NormalizationWarning(ballot_id=0, code=None, reason="排名不是数组", position=None)
        ]

    for index, code in enumerate(raw_rankings, start=1):
        if not isinstance(code, str):
            warnings.append(
                NormalizationWarning(
                    ballot_id=0, code=str(code), reason="候选人代码必须是字符串", position=index
                )
            )
            continue
        if code not in valid_codes:
            warnings.append(
                NormalizationWarning(
                    ballot_id=0, code=code, reason="无效或不属于本次选举的候选人代码，已忽略", position=index
                )
            )
            continue
        if code in seen:
            warnings.append(
                NormalizationWarning(
                    ballot_id=0,
                    code=code,
                    reason="同一候选人重复排名，只保留第一次出现的最高偏好，后续重复项已忽略",
                    position=index,
                )
            )
            continue
        seen.add(code)
        normalized.append(code)

    return normalized, warnings


def _candidate_sort_rank(destination, code_to_candidate_order):
    if destination is None:
        return float("inf")
    return code_to_candidate_order[destination]


def tally_irv(election):
    """Compute a round-by-round single-winner IRV result.

    The tally never mutates stored ballots. At the end of each round active
    candidate totals are compared with a majority of ballots currently
    assigned to a candidate (valid ballots). If nobody wins, the lowest total
    is eliminated; ties are resolved by the preconfigured candidate tie order,
    with no randomness. Each ballot then moves to its next active preference
    or becomes exhausted.
    """
    candidates = sorted(election.candidates.all(), key=lambda c: c.code)
    code_to_candidate = {candidate.code: candidate for candidate in candidates}
    candidate_order = {candidate.code: index for index, candidate in enumerate(candidates)}
    ballots = list(election.ballots.all().order_by("synthetic_ballot_id"))

    active_codes = {candidate.code for candidate in candidates}
    assignments = {}

    # First-round assignment is the first normalized preference, or exhausted.
    for ballot in ballots:
        rankings = ballot.normalized_rankings
        assignments[ballot.id] = rankings[0] if rankings else None

    rounds = []
    round_number = 1
    previous_round = None

    while True:
        valid_ballot_ids = [
            ballot.id for ballot in ballots if assignments[ballot.id] in active_codes
        ]
        exhausted_ballot_numbers = sorted(
            ballot.synthetic_ballot_id for ballot in ballots if assignments[ballot.id] is None
        )
        valid_total = len(valid_ballot_ids)
        exhausted_total = len(exhausted_ballot_numbers)
        majority_threshold = (valid_total // 2) + 1 if valid_total else 0

        totals = {code: 0 for code in active_codes}
        for ballot_id in valid_ballot_ids:
            totals[assignments[ballot_id]] += 1

        ranked_active = sorted(
            active_codes,
            key=lambda code: (totals[code], code),
        )
        winner_code = None
        if len(active_codes) == 1:
            winner_code = next(iter(active_codes))
            status = "winner"
        elif ranked_active and totals[ranked_active[-1]] > valid_total / 2:
            winner_code = ranked_active[-1]
            status = "winner"
        else:
            status = "elimination"

        eliminated_code = None
        if status == "elimination":
            eliminated_code = ranked_active[0]
            min_total = totals[eliminated_code]
            tied_codes = sorted(
                code for code in active_codes if totals[code] == min_total
            )
            eliminated_code = tied_codes[0]

        candidate_results = []
        for candidate in candidates:
            code = candidate.code
            candidate_results.append(
                {
                    "code": code,
                    "name": candidate.name,
                    "votes": totals.get(code, 0),
                    "active": code in active_codes,
                    "is_winner": code == winner_code,
                    "eliminated_after_round": round_number if code == eliminated_code else None,
                }
            )

        # Describe where every ballot is after this round's assignment.
        ballot_tracks = [
            {
                "ballot_id": ballot.synthetic_ballot_id,
                "rankings": ballot.normalized_rankings,
                "destination": assignments[ballot.id],
                "exhausted": assignments[ballot.id] is None,
            }
            for ballot in ballots
        ]

        transfers = []
        if previous_round is not None:
            grouped = {}
            for ballot in ballots:
                source = previous_round["_assignments"][ballot.id]
                destination = assignments[ballot.id]
                if source == destination:
                    continue
                key = (source, destination)
                grouped.setdefault(key, []).append(ballot.synthetic_ballot_id)

            for (source, destination), ballot_ids in grouped.items():
                transfers.append(
                    {
                        "source_code": source,
                        "destination_code": destination,
                        "destination_is_exhausted": destination is None,
                        "count": len(ballot_ids),
                        "ballot_ids": sorted(ballot_ids),
                    }
                )
            transfers.sort(
                key=lambda item: (
                    _candidate_sort_rank(item["source_code"], candidate_order),
                    item["source_code"] or "",
                    _candidate_sort_rank(item["destination_code"], candidate_order),
                    item["destination_code"] or "",
                )
            )

        round_record = {
            "round_number": round_number,
            "status": status,
            "valid_total": valid_total,
            "exhausted_total": exhausted_total,
            "exhausted_ballot_ids": exhausted_ballot_numbers,
            "total_ballots": len(ballots),
            "majority_threshold": majority_threshold,
            "winner_code": winner_code,
            "eliminated_code": eliminated_code,
            "tie_break_applied": bool(
                eliminated_code
                and len(
                    [
                        code
                        for code, total in totals.items()
                        if total == totals[eliminated_code]
                    ]
                )
                > 1
            ),
            "candidate_results": candidate_results,
            "transfers": transfers,
            "ballot_tracks": ballot_tracks,
            "_assignments": assignments,
        }
        rounds.append(round_record)

        if status == "winner":
            break

        # Move to the next round. All ballots for the eliminated candidate are
        # transferred; other ballots remain with their current candidate.
        active_codes.remove(eliminated_code)
        next_assignments = dict(assignments)
        for ballot in ballots:
            if assignments[ballot.id] != eliminated_code:
                continue
            next_destination = None
            for code in ballot.normalized_rankings:
                if code in active_codes:
                    next_destination = code
                    break
            next_assignments[ballot.id] = next_destination

        assignments = next_assignments
        previous_round = round_record
        round_number += 1

    for record in rounds:
        record.pop("_assignments", None)

    return {
        "rounds": rounds,
        "total_ballots": len(ballots),
        "winner_code": rounds[-1]["winner_code"],
    }
