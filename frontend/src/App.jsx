import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import RulesPanel from "./components/RulesPanel.jsx";
import RoundCard from "./components/RoundCard.jsx";
import BallotList from "./components/BallotList.jsx";

export default function App() {
  const [elections, setElections] = useState([]);
  const [electionId, setElectionId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [result, setResult] = useState(null);
  const [showBallots, setShowBallots] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listElections()
      .then((rows) => {
        setElections(rows);
        if (rows.length) setElectionId(rows[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!electionId) return;
    setLoading(true);
    setResult(null);
    Promise.all([
      api.getElection(electionId),
      api.getCandidates(electionId),
      api.getResult(electionId),
    ])
      .then(([e, c, r]) => {
        setDetail(e);
        setCandidates(c);
        setResult(r);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [electionId]);

  const maxVotes = useMemo(() => {
    if (!result) return 1;
    return Math.max(
      1,
      ...result.rounds.flatMap((r) =>
        r.tally_rows
          .filter((row) => row.votes !== null)
          .map((row) => row.votes)
      )
    );
  }, [result]);

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>单席位排序选择投票（IRV）计票系统</h1>
          <p className="subtitle">
            逐轮展示候选人得票、选票转移与穷尽票 ·
            <span className="synthetic-badge">
              全部为匿名合成数据，不接入任何真实选举
            </span>
          </p>
        </div>
      </header>

      {error && <div className="error-box">加载失败：{error}</div>}

      <section className="election-picker">
        <label htmlFor="election-select">选择选举：</label>
        <select
          id="election-select"
          value={electionId ?? ""}
          onChange={(e) => setElectionId(Number(e.target.value))}
        >
          {elections.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}
            </option>
          ))}
        </select>
      </section>

      {loading && <div className="hint">正在从 PostgreSQL 读取合成数据…</div>}

      {detail && result && (
        <>
          <Summary detail={detail} result={result} />
          <RulesPanel ruleset={detail.ruleset} order={result.tie_break_order} />

          <h2 className="section-title">
            逐轮计票（共 {result.rounds.length} 轮）
          </h2>
          <ol className="rounds">
            {result.rounds.map((round) => (
              <li key={round.round_number}>
                <RoundCard
                  round={round}
                  maxVotes={maxVotes}
                />
              </li>
            ))}
          </ol>

          <WinnerBanner result={result} />

          <section className="ballots-section">
            <button
              className="link-button"
              onClick={() => setShowBallots((v) => !v)}
            >
              {showBallots ? "▾ 收起匿名合成选票明细" : "▸ 查看匿名合成选票明细"}
            </button>
            {showBallots && (
              <BallotList electionId={electionId} candidates={candidates} />
            )}
          </section>
        </>
      )}

      <footer className="footer">
        计票规则在选举前固定；同票按候选人代码字典序决胜，全程无随机数。
      </footer>
    </div>
  );
}

function Summary({ detail, result }) {
  return (
    <section className="summary-grid">
      <div className="summary-item">
        <span className="summary-label">合成选票总数</span>
        <span className="summary-value">{result.total_ballots}</span>
      </div>
      <div className="summary-item">
        <span className="summary-label">有效票</span>
        <span className="summary-value">{result.total_valid_weight}</span>
      </div>
      <div className="summary-item">
        <span className="summary-label">入库无效票</span>
        <span className="summary-value">
          {result.invalid_ballots}
          <small>（未给任何有效排名）</small>
        </span>
      </div>
      <div className="summary-item">
        <span className="summary-label">票数守恒校验</span>
        <span
          className={`summary-value ${
            result.conservation_ok ? "ok" : "bad"
          }`}
        >
          {result.conservation_ok ? "✓ 每轮守恒" : "✗ 异常"}
        </span>
      </div>
    </section>
  );
}

function WinnerBanner({ result }) {
  if (!result.winner_code) return null;
  const last = result.rounds[result.rounds.length - 1];
  const majorityText =
    result.terminated_reason === "majority"
      ? "获得严格过半"
      : "其余候选人均被淘汰（无人过半时最后在场者）";
  return (
    <section className="winner-banner">
      <div>
        <strong>最终当选：</strong>
        <span className="winner-name">
          {result.winner_code} · {result.winner_name}
        </span>
      </div>
      <div className="winner-meta">
        末轮得票 {last.active_ballots} 张在投中的
        {last.tally_rows.find((r) => r.code === result.winner_code)?.votes}{" "}
        张 · 过半门槛 {last.majority_threshold} · {majorityText}
      </div>
    </section>
  );
}
