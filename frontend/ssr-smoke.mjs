// 组件服务端渲染冒烟测试：用真实 API 数据结构渲染所有组件，
// 若引用了不存在的字段会直接抛错。用 node ssr-smoke.mjs 运行。
import React from "react";
import { renderToString } from "react-dom/server";
import RulesPanel from "./src/components/RulesPanel.jsx";
import RoundCard from "./src/components/RoundCard.jsx";
import BallotList from "./src/components/BallotList.jsx";

const ruleset = {
  name: "标准 IRV 规则",
  duplicate_rank_handling: "dedup_first",
  invalid_candidate_handling: "drop_invalid",
  unranked_handling: "exhaust_when_gone",
  majority_rule: "strict_majority",
  tie_break: "code_asc",
  description: "测试规则说明",
};

const round3 = {
  round_number: 3,
  transfers_in: [
    { from_code: "D", from_name: "丁", to_code: "A", to_name: "甲", votes: 1 },
    { from_code: "D", from_name: "丁", to_code: "B", to_name: "乙", votes: 1 },
    { from_code: "D", from_name: "丁", to_code: null,
      to_name: "穷尽（无下一有效偏好）", votes: 2 },
  ],
  exhausted_delta: 2,
  tally_rows: [
    { code: "A", name: "甲", votes: 8, status: "standing" },
    { code: "B", name: "乙", votes: 10, status: "standing" },
    { code: "C", name: "丙", votes: null, status: "eliminated" },
    { code: "D", name: "丁", votes: null, status: "eliminated" },
  ],
  active_ballots: 18,
  exhausted_ballots: 2,
  counted_ballots: 20,
  majority_threshold: 11,
  min_votes: 8,
  tied_min_codes: ["A"],
  eliminated_codes: ["A"],
  eliminated_name: "甲",
  elected_code: null,
  elected_name: null,
  terminal_reason: null,
};

const round4 = {
  ...round3,
  round_number: 4,
  transfers_in: [
    { from_code: "A", from_name: "甲", to_code: "B", to_name: "乙", votes: 5 },
    { from_code: "A", from_name: "甲", to_code: null,
      to_name: "穷尽（无下一有效偏好）", votes: 3 },
  ],
  exhausted_delta: 3,
  tally_rows: [
    { code: "A", name: "甲", votes: null, status: "eliminated" },
    { code: "B", name: "乙", votes: 15, status: "standing" },
    { code: "C", name: "丙", votes: null, status: "eliminated" },
    { code: "D", name: "丁", votes: null, status: "eliminated" },
  ],
  active_ballots: 15,
  exhausted_ballots: 5,
  counted_ballots: 20,
  majority_threshold: 11,
  min_votes: null,
  tied_min_codes: [],
  eliminated_codes: [],
  eliminated_name: null,
  elected_code: "B",
  elected_name: "乙",
  terminal_reason: "majority",
};

let html = "";
html += renderToString(
  React.createElement(RulesPanel, { ruleset, order: ["A", "B", "C", "D"] })
);
for (const r of [round3, round4]) {
  html += renderToString(
    React.createElement(RoundCard, { round: r, maxVotes: 15 })
  );
}
html += renderToString(
  React.createElement(BallotList, {
    electionId: 1,
    candidates: [
      { code: "A", name: "甲" }, { code: "B", name: "乙" },
      { code: "C", name: "丙" }, { code: "D", name: "丁" },
    ],
  })
);

const checks = [
  ["规则决胜顺序", html.includes("A → B → C → D")],
  ["穷尽票标签", html.includes("穷尽（无下一有效偏好）")],
  ["当选标记", html.includes("✓ 当选")],
  ["门槛", html.includes("&gt;10")],
];
for (const [name, ok] of checks) {
  console.log(`${ok ? "✓" : "✗"} ${name}`);
  if (!ok) process.exitCode = 1;
}
console.log(`SSR 输出 ${html.length} 字符，组件全部成功渲染，无运行时异常`);
