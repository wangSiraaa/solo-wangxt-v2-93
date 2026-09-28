import React from "react";

export default function RoundCard({ round, maxVotes }) {
  const pct = (v) => Math.round((v / Math.max(maxVotes, 1)) * 1000) / 10;
  const sharePct = (v) =>
    Math.round((v / Math.max(round.counted_ballots, 1)) * 1000) / 10;

  return (
    <article className={`round-card ${round.elected_code ? "terminal" : ""}`}>
      <header className="round-head">
        <h3>
          第 {round.round_number} 轮
          {round.elected_code && <span className="tag elected-tag">当选轮</span>}
        </h3>
        <div className="round-metrics">
          <Metric label="在投有效票" value={round.active_ballots} />
          <Metric label="穷尽票" value={round.exhausted_ballots} warn />
          <Metric label="计入分母" value={round.counted_ballots} />
          <Metric label="过半门槛" value={`>${Math.floor(round.counted_ballots / 2)}`} strong />
        </div>
      </header>

      <div className="tally">
        {round.tally_rows.map((row) => (
          <div
            key={row.code}
            className={`cand-row status-${row.status}`}
          >
            <div className="cand-id">
              <span className="cand-code">{row.code}</span>
              <span className="cand-name">{row.name}</span>
              {row.status === "eliminated" && (
                <span className="tag out-tag">已淘汰</span>
              )}
              {round.elected_code === row.code && (
                <span className="tag win-tag">✓ 当选</span>
              )}
            </div>
            <div className="bar-track">
              {row.votes !== null && row.votes > 0 && (
                <div
                  className={`bar-fill ${
                    row.votes >= round.majority_threshold
                      ? "bar-over"
                      : ""
                  }`}
                  style={{ width: `${pct(row.votes)}%` }}
                />
              )}
            </div>
            <div className="cand-votes">
              {row.votes === null ? (
                <span className="muted">—</span>
              ) : (
                <>
                  <strong>{row.votes}</strong>
                  <small>票 · 占分母 {sharePct(row.votes)}%</small>
                  {row.votes >= round.majority_threshold && (
                    <span className="over-mark">已过半</span>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {round.transfers_in.length > 0 && (
        <TransferBox round={round} />
      )}

      {round.tied_min_codes.length > 1 && (
        <p className="tie-note">
          本轮最低票 {round.min_votes} 票出现并列：
          <strong>{round.tied_min_codes.join("、")}</strong>
          ，按事先配置的候选人代码顺序淘汰
          <strong> {round.eliminated_codes.join("、")}</strong>
          （{round.eliminated_name}），不做随机选择。
        </p>
      )}

      {round.terminal_reason === "acclamation_last_standing" && (
        <p className="tie-note">
          穷尽票导致无人能达到过半门槛，仅剩一名在场候选人，
          按规则由其当选。
        </p>
      )}
    </article>
  );
}

function Metric({ label, value, warn, strong }) {
  return (
    <span className={`metric ${warn ? "metric-warn" : ""} ${strong ? "metric-strong" : ""}`}>
      {label} <b>{value}</b>
    </span>
  );
}

function TransferBox({ round }) {
  const totalMoved = round.transfers_in.reduce((s, t) => s + t.votes, 0);
  return (
    <div className="transfer-box">
      <h4>
        选票转移汇总
        <small>（上一轮淘汰后的票在本轮的去向，共 {totalMoved} 张）</small>
      </h4>
      <ul>
        {round.transfers_in.map((t, i) => (
          <li key={i} className={t.to_code === null ? "to-exhausted" : ""}>
            <span className="flow">
              <span className="flow-code">{t.from_code}</span>
              <span className="flow-name">{t.from_name}</span>
              <span className="arrow">→</span>
              {t.to_code === null ? (
                <span className="flow-exhausted">穷尽（无下一有效偏好）</span>
              ) : (
                <>
                  <span className="flow-code">{t.to_code}</span>
                  <span className="flow-name">{t.to_name}</span>
                </>
              )}
            </span>
            <span className="flow-votes">
              <b>{t.votes}</b> 票
            </span>
          </li>
        ))}
      </ul>
      {round.exhausted_delta > 0 && (
        <p className="exhausted-delta">
          本轮新增穷尽票 <b>{round.exhausted_delta}</b> 张：
          这些选票已排名的候选人全部被淘汰，且未给其他候选人排名，
          不再计入任何候选人，但仍留在过半门槛的分母中。
        </p>
      )}
    </div>
  );
}
