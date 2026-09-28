const BASE = "/api";

async function get(path) {
  const resp = await fetch(`${BASE}${path}`);
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText}`);
  }
  return resp.json();
}

export const api = {
  listElections: () => get("/elections/"),
  getElection: (id) => get(`/elections/${id}/`),
  getCandidates: (id) => get(`/elections/${id}/candidates/`),
  getBallots: (id) => get(`/elections/${id}/ballots/`),
  getResult: (id) => get(`/elections/${id}/result/`),
};
