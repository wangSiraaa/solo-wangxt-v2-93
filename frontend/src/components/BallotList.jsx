import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function BallotList({ electionId, candidates }) {
  const [ballots, setBallots] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api.getBallots(electionId).then(setBallots);
  }, [electionId]);

  if (!ballots) return <p className="hint">读取选票中…</p>;

  const shown = ballots.filter((b) =>
    filter === "all" ? true : filter === "valid" ? b.is_valid : !b.is_valid
  );

  const nameOf = (code) =>
    candidates.find((c) => c.code === code)?.name ?? code;

  return (
    <div className="ballot-box">
      <div className="ballot-filters">
        {[
          ["all", `全部（${ballots.length}）`],
          ["valid", `有效（${ballots.filter((b) => b.is_valid).length}）`],
          ["invalid", `无效（${ballots.filter((b) => !b.is_valid).length}）`],
        ].map(([key, label]) => (
          <button
            key={key}
            className={`chip ${filter === key ? "chip-on" : ""}`}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>
      <table className="ballot-table">
        <thead>
          <tr>
            <th>#</th>
            <th>原始偏好序列</th>
            <th>清洗后偏好</th>
            <th>状态 / 原因</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((b, i) => (
            <tr key={b.id} className={b.is_valid ? "" : "row-invalid"}>
              <td>{i + 1}</td>
              <td>
                <code>{JSON.stringify(b.preferences_raw)}</code>
              </td>
              <td>
                {b.is_valid ? (
                  <code>
                    {b.preferences
                      .map((c) => `${c}(${nameOf(c)})`)
                      .join(" > ")}
                  </code>
                ) : (
                  <span className="muted">— 不参与计票 —</span>
                )}
              </td>
              <td>
                {b.is_valid ? (
                  <span className="ok-text">
                    有效{b.invalid_reason ? `（${b.invalid_reason}）` : ""}
                  </span>
                ) : (
                  <span className="bad-text">无效：{b.invalid_reason}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
