"""选票清洗：把原始偏好序列按本次规则变成有效偏好序列。"""
from __future__ import annotations

from typing import Any


def normalize_preferences(
    raw: Any, valid_codes: set[str]
) -> tuple[list[str], bool, str]:
    """返回 (清洗后偏好, 是否有效, 原因说明)。

    规则（由 RuleSet 固定，不接受临场更改）：
    1. 非列表、None 一律视为空偏好；
    2. 每个元素转成去除首尾空白的字符串，空串忽略；
    3. 代码不在本次候选人集合内 -> 无效候选人，剔除该项并记录；
    4. 同一代码在一张票上重复排名同一代码多次 -> 只保留第一次出现的位置；
    5. 清洗后为空 -> 整票无效（未给任何有效排名），不参与任何一轮。

    序列里没有的代码即视为“未排名该候选人”。
    """
    notes: list[str] = []
    if raw is None:
        return [], False, "原始偏好为空：未给任何候选人排名"
    if not isinstance(raw, list):
        return [], False, "原始偏好不是排名序列"

    seen: set[str] = set()
    cleaned: list[str] = []
    invalid_hits: list[str] = []

    for item in raw:
        code = str(item).strip() if item is not None else ""
        if not code:
            continue
        if code not in valid_codes:
            if code not in invalid_hits:
                invalid_hits.append(code)
            continue
        if code in seen:
            notes.append(f"重复排名 {code}：保留首次位置")
            continue
        seen.add(code)
        cleaned.append(code)

    if invalid_hits:
        notes.insert(0, f"无效候选人代码 {invalid_hits}：已剔除该项")

    if not cleaned:
        reason = "清洗后无任何有效偏好（未排名或全部无效）"
        if invalid_hits:
            reason = f"含无效代码 {invalid_hits}，且无其他有效排名"
        return [], False, reason

    return cleaned, True, "；".join(notes)
