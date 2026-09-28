import { useEffect, useMemo, useState } from 'react';

const API_BASE = '/api';

function candidateName(election, code) {
  return election?.candidates.find((candidate) => candidate.code === code)?.name || code;
}

function transferText(item, election) {
  const destination = item.destination_is_exhausted
    ? '穷尽票'
    : `${item.destination_code} ${candidateName(election, item.destination_code)}`;
  const source = `${item.source_code} ${candidateName(election, item.source_code)}`;
  return `${source} → ${destination}：${item.count} 票（选票 #${item.ballot_ids.join('、#')}）`;
}

function RoundCard({ round, election }) {
  const eliminated = round.eliminated_code
    ? `${round.eliminated_code} ${candidateName(election, round.eliminated_code)}`
    : null;
  const winner = round.winner_code
    ? `${round.winner_code} ${candidateName(election, round.winner_code)}`
    : null;

  return (
    <section className="round-card">
      <header className="round-header">
        <div>
          <p className="eyebrow">第 {round.round_number} 轮</p>
          <h2>{round.status === 'winner' ? '产生当选人' : '无人过半，进入转移'}</h2>
        </div>
        <span className={`badge ${round.status === 'winner' ? 'winner' : 'eliminate'}`}>
          {round.status === 'winner' ? `当选：${winner}` : `淘汰：${eliminated}`}
        </span>
      </header>

      <div className="stats-grid">
        <div><strong>{round.valid_total}</strong><span>有效票</span></div>
        <div><strong>{round.exhausted_total}</strong><span>穷尽票</span></div>
        <div><strong>{round.majority_threshold}</strong><span>过半阈值</span></div>
        <div><strong>{round.total_ballots}</strong><span>合成选票总数</span></div>
      </div>

      <div className="candidate-table-wrap">
        <table className="candidate-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>候选人</th>
              <th>本轮票数</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {round.candidate_results.map((candidate) => (
              <tr key={candidate.code} className={candidate.is_winner ? 'is-winner' : ''}>
                <td>{candidate.code}</td>
                <td>{candidate.name}</td>
                <td><strong>{candidate.active ? candidate.votes : '—'}</strong></td>
                <td>
                  {candidate.is_winner
                    ? '当选'
                    : candidate.eliminated_after_round === round.round_number
                      ? `本轮淘汰${round.tie_break_applied ? '（同票按代码顺序决胜）' : ''}`
                      : candidate.active
                        ? '在局'
                        : '已淘汰'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="transfer-panel">
        <h3>选票去向 / 转移汇总</h3>
        {round.transfers.length === 0 ? (
          <p className="muted">首轮按每张选票的最高有效偏好分配；另有首轮即穷尽的选票计入穷尽票。</p>
        ) : (
          <ul>
            {round.transfers.map((item) => (
              <li key={`${item.source_code}-${item.destination_code || 'exhausted'}`}>
                {transferText(item, election)}
              </li>
            ))}
          </ul>
        )}
        <p className="conservation">
          守恒校验：候选人票数合计 {round.valid_total} + 穷尽票 {round.exhausted_total} = {round.total_ballots}
          ；穷尽选票：#{round.exhausted_ballot_ids.join('、#') || '无'}
        </p>
      </div>
    </section>
  );
}

export default function App() {
  const [elections, setElections] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [tally, setTally] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/elections/`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`选举列表加载失败：${response.status}`);
        return response.json();
      })
      .then((data) => {
        setElections(data);
        setSelectedId(String(data[0]?.id || ''));
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return undefined;
    setLoading(true);
    setError('');
    fetch(`${API_BASE}/elections/${selectedId}/tally/`)
      .then(async (response) => {
        if (!response.ok) throw new Error(`计票结果加载失败：${response.status}`);
        return response.json();
      })
      .then(setTally)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedId]);

  const winner = useMemo(() => {
    if (!tally) return null;
    const code = tally.winner_code;
    const candidate = tally.election.candidates.find((item) => item.code === code);
    return candidate ? `${candidate.code} ${candidate.name}` : code;
  }, [tally]);

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">单席位排序选择投票 · IRV</p>
          <h1>社团联合会计票解释台</h1>
          <p>
            仅使用匿名合成数据。逐轮展示有效票、穷尽票、最低票淘汰、下一有效偏好转移和固定代码顺序决胜。
          </p>
        </div>
        <label className="election-picker">
          选择演示选举
          <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
            {elections.length === 0 && <option value="">暂无演示选举</option>}
            {elections.map((election) => (
              <option key={election.id} value={election.id}>{election.title}</option>
            ))}
          </select>
        </label>
      </section>

      {loading && <div className="notice">加载中…</div>}
      {error && <div className="notice error">{error}</div>}

      {tally && (
        <>
          <section className="summary-panel">
            <div>
              <p className="eyebrow">最终结果</p>
              <h2>{winner} 当选</h2>
              <p>{tally.election.description}</p>
            </div>
            <div className="rules">
              <h3>本次规则</h3>
              <ul>
                <li><strong>重复排名：</strong>{tally.rules.duplicate_rankings}</li>
                <li><strong>未排名候选：</strong>{tally.rules.unranked_candidates}</li>
                <li><strong>无效候选：</strong>{tally.rules.invalid_candidates}</li>
                <li><strong>同票决胜：</strong>{tally.rules.tie_break}</li>
              </ul>
            </div>
          </section>

          <div className="rounds">
            {tally.rounds.map((round) => (
              <RoundCard key={round.round_number} round={round} election={tally.election} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
