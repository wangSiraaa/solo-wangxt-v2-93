import React from "react";

const HANDLING_TEXT = {
  dedup_first: "同票重复排名同一候选人：保留其最先出现的位置，删除后续重复项",
  drop_invalid: "出现无效（本次不存在的）候选人代码：剔除该无效项，其余偏好保留",
  exhaust_when_gone:
    "未排名的候选人不参与该票分配；当票上所有已排名候选人均被淘汰，该票成为穷尽票",
  strict_majority:
    "当选门槛为严格过半（votes > 有效票/2），穷尽票每轮仍计入分母",
  code_asc: "最低票并列时，按候选人代码升序先淘汰（事先配置，禁止临时随机）",
};

export default function RulesPanel({ ruleset, order }) {
  const rows = [
    ["重复排名", ruleset.duplicate_rank_handling],
    ["无效候选人代码", ruleset.invalid_candidate_handling],
    ["未排名候选人", ruleset.unranked_handling],
    ["过半口径", ruleset.majority_rule],
    ["同票决胜", ruleset.tie_break],
  ];
  return (
    <section className="rules-panel">
      <h2 className="section-title">本次计票规则（{ruleset.name}）</h2>
      <ul className="rules-list">
        {rows.map(([label, key]) => (
          <li key={label}>
            <em>{label}：</em>
            <span>{HANDLING_TEXT[key] || key}</span>
          </li>
        ))}
        <li>
          <em>决胜代码顺序：</em>
          <span>{order.join(" → ")}</span>
        </li>
      </ul>
      {ruleset.description && (
        <p className="rules-desc">{ruleset.description}</p>
      )}
    </section>
  );
}
