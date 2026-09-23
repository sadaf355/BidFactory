import React, { useEffect, useState } from "react";
import "./index.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function api(path, options = {}) {
  const response = await fetch(API + path, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export default function App() {
  const [page, setPage] = useState("Dashboard");
  const [requirements, setRequirements] = useState([]);
  const [requirementDetails, setRequirementDetails] = useState([]);
  const [rfp, setRfp] = useState(null);
  const [results, setResults] = useState([]);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [bids, setBids] = useState([]);
  const [memory, setMemory] = useState([]);
  const [dashboard, setDashboard] = useState({});
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeResults, setKnowledgeResults] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const nav = [
    "Dashboard", "RFP Workspace", "Compliance Matrix",
    "Human Review", "Final Bid", "Knowledge Base", "Bid Memory"
  ];

  const refresh = async () => {
    try {
      const [r, b, m, d] = await Promise.all([
        api("/reviews"),
        api("/bids"),
        api("/outcomes/memory"),
        api("/dashboard/summary")
      ]);
      setReviews(r);
      setBids(b);
      setMemory(m);
      setDashboard(d);
    } catch (_) {}
  };

  useEffect(() => { refresh(); }, []);

  async function uploadRfp(file) {
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", file);
      const data = await api("/rfps/upload", { method: "POST", body: form });
      applyRfpData(data);
      setMessage(`Extracted ${data.requirement_count} requirements from ${data.filename}`);
    } catch (e) {
      setMessage("Upload failed: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadDemoRfp() {
    setBusy(true);
    setMessage("");
    try {
      const data = await api("/rfps/demo");
      applyRfpData(data);
      setMessage(`Loaded demo RFP — ${data.requirement_count} requirements extracted from ${data.filename}.`);
    } catch (e) {
      setMessage("Could not load demo data: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  function applyRfpData(data) {
    setRfp(data);
    const details = data.requirements || [];
    setRequirementDetails(details);
    setRequirements(details.map(r => r.text));
    setPage("RFP Workspace");
  }

  async function analyze() {
    const clean = requirements.map(x => x.trim()).filter(Boolean);
    if (!clean.length) return setMessage("Add at least one requirement.");
    setBusy(true);
    try {
      // Carry classification (category/mandatory) through for lines that
      // still match an extracted requirement; manually added/edited lines
      // are sent as plain text and get classified server-side instead.
      const byText = Object.fromEntries(requirementDetails.map(r => [r.text.trim(), r]));
      const payload = clean.map(text => {
        const match = byText[text];
        return match ? { text, category: match.category, mandatory: match.mandatory } : text;
      });

      const data = await api("/analysis/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements: payload })
      });
      setResults(data.results || []);
      setPage("Compliance Matrix");
      setMessage("Analysis completed using retrieval + multi-agent workflow.");
    } catch (e) {
      setMessage("Analysis failed: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function createReview(item) {
    await api("/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requirement: item.requirement,
        analysis: item,
        draft_response: item.draft_response
      })
    });
    await refresh();
    setPage("Human Review");
  }

  async function decideReview(id, status) {
    let edited_response;
    if (status === "EDITED") {
      edited_response = prompt("Enter the revised response:");
      if (edited_response === null) return;
    }
    await api(`/reviews/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status, edited_response })
    });
    refresh();
  }

  async function assembleBid() {
    if (!results.length) return;
    setBusy(true);
    try {
      const merged = results.map(item => {
        const review = reviews.find(r =>
          r.requirement === item.requirement &&
          ["APPROVED", "EDITED"].includes(r.status)
        );
        return review?.edited_response ? { ...item, edited_response: review.edited_response } : item;
      });
      const bid = await api("/bids/assemble", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_results: merged,
          company_name: "NovaTech Solutions",
          title: rfp ? `Bid Response — ${rfp.filename}` : "Bid Response"
        })
      });
      setBids(prev => [...prev, bid]);
      setPage("Final Bid");
    } finally {
      setBusy(false);
    }
  }

  async function recordOutcome(outcome) {
    await api("/outcomes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rfp_name: rfp?.filename || "Current Demo RFP",
        outcome,
        notes: "Outcome recorded from final BidFactory submission.",
        lessons: ["This win/loss result is now searchable as future Bid Memory."]
      })
    });
    await refresh();
    setPage("Bid Memory");
  }

  async function searchKnowledge() {
    if (!knowledgeQuery.trim()) return;
    const data = await api(`/knowledge-base/search?q=${encodeURIComponent(knowledgeQuery)}&top_k=10`);
    setKnowledgeResults(data.results || []);
  }

  return (
    <div className="shell">
      <aside>
        <h1>BidFactory</h1>
        <small>AI Bid Intelligence</small>
        <div className="workflow-badge">5-Agent Pipeline</div>
        <nav>
          {nav.map((item, i) => (
            <button key={item} className={page === item ? "active" : ""} onClick={() => setPage(item)}>
              <span className="tab-index">{String(i + 1).padStart(2, "0")}</span>
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <main>
        <div className="topbar">
          <span className="eyebrow">Case File</span>
          <span className="case-ref">{rfp ? rfp.filename : "No active RFP loaded"}</span>
        </div>
        {message && <div className="message">{message}</div>}

        {page === "Dashboard" && <>
          <h2>Dashboard</h2>
          <div className="cards">
            <Card title="Requirements" value={results.length} />
            <Card title="Pending Reviews" value={dashboard.reviews?.pending || reviews.filter(x => x.status === "PENDING").length} />
            <Card title="Final Bids" value={dashboard.bids ?? bids.length} />
            <Card title="Bid Memory" value={dashboard.bid_memory ?? memory.length} />
          </div>
          <section className="panel">
            <h3>End-to-End Bid Flow</h3>
            <div className="flow">
              <span>Upload RFP</span><b>→</b><span>Extract</span><b>→</b><span>Retrieve</span>
              <b>→</b><span>Agents</span><b>→</b><span>Review</span><b>→</b>
              <span>Bid</span><b>→</b><span>WIN/LOSS</span>
            </div>
          </section>
        </>}

        {page === "RFP Workspace" && <>
          <h2>RFP Workspace</h2>
          <section className="panel">
            <h3>1. Upload RFP / Tender</h3>
            <input type="file" accept=".pdf,.docx,.txt,.md"
              onChange={e => uploadRfp(e.target.files?.[0])} />
            <button onClick={loadDemoRfp} disabled={busy}>
              {busy ? "Loading..." : "Continue with Demo Data"}
            </button>
            <p><small>Runs the real bundled sample RFP through the real pipeline — useful for a live demo without a file to hand.</small></p>
            {busy && <p>Processing document...</p>}
            {rfp && <p><b>{rfp.filename}</b> — {rfp.requirement_count} requirements extracted
              {rfp.extraction_source && <small> ({rfp.extraction_source === "llm" ? "LLM-classified" : "keyword fallback"})</small>}.
            </p>}
          </section>

          {requirementDetails.length > 0 && <section className="panel">
            <h3>2. Requirement List</h3>
            <table>
              <thead><tr><th>ID</th><th>Requirement</th><th>Category</th><th>Priority</th></tr></thead>
              <tbody>
                {requirementDetails.map(r => <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.text}</td>
                  <td>{r.category}</td>
                  <td>{r.mandatory ? "Mandatory" : "Optional"}</td>
                </tr>)}
              </tbody>
            </table>
          </section>}

          <section className="panel">
            <h3>3. Extracted Requirements</h3>
            <p>Review or edit the extracted requirements before running analysis.</p>
            <textarea
              value={requirements.join("\n")}
              onChange={e => setRequirements(e.target.value.split("\n"))}
              placeholder="Upload an RFP, load demo data, or enter one requirement per line"
            />
            <button className="primary" onClick={analyze} disabled={busy}>
              {busy ? "Running..." : "Run Analysis"}
            </button>
          </section>
        </>}

        {page === "Compliance Matrix" && <>
          <h2>Compliance Matrix</h2>
          <table>
            <thead><tr><th>Requirement</th><th>Category</th><th>Status</th><th>Evidence</th><th>Decision</th></tr></thead>
            <tbody>
              {results.map((item, i) => <tr key={i}>
                <td>{item.requirement}</td>
                <td>{item.category}{item.mandatory === false && <div><small>Optional</small></div>}</td>
                <td className={item.status}>{item.status}</td>
                <td>{(item.evidence || []).slice(0, 3).map((e, j) =>
                  <div className="evidence" key={j}><b>{e.source}</b><br/><small>{e.text?.slice(0, 160)}</small></div>
                )}</td>
                <td>{item.human_review
                  ? <button onClick={() => createReview(item)}>Send to Review</button>
                  : "Auto-ready"}
                  <div className="answer-source">
                    {item.answer_source === "llm" ? "GPT-drafted" : "Rule-based draft"}
                  </div>
                  <button onClick={() => setSelectedDetail(item)}>View Details</button>
                </td>
              </tr>)}
            </tbody>
          </table>
          <button className="primary" onClick={assembleBid} disabled={!results.length || busy}>Assemble Final Bid</button>
        </>}

        {selectedDetail && <div className="modal-overlay" onClick={() => setSelectedDetail(null)}>
          <div className="modal-panel" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedDetail(null)}>Close</button>
            <h3>Requirement Detail</h3>
            <p><b>{selectedDetail.requirement}</b></p>
            <p>
              <span className={`status ${selectedDetail.status}`}>{selectedDetail.status}</span>
              {" "}Confidence: {selectedDetail.confidence != null ? Math.round(selectedDetail.confidence * 100) + "%" : "—"}
            </p>

            <h4>Evidence Used</h4>
            {(selectedDetail.evidence || []).length === 0 && <p><small>No evidence retrieved.</small></p>}
            {(selectedDetail.evidence || []).map((e, j) => <div className="evidence" key={j}>
              <b>{e.source}</b> <span className="score">score {e.score}</span>
              <p><small>{e.text}</small></p>
            </div>)}

            <h4>Agent Opinions</h4>
            {selectedDetail.agents ? Object.entries(selectedDetail.agents).map(([name, out]) => (
              <div className="panel" key={name}>
                <b>{out?.agent || name.replace(/_/g, " ")}</b>
                {/* Strategist */}
                {out?.positioning && <div><small>{out.positioning}</small></div>}
                {/* Compliance / Adjudicator */}
                {out?.assessment && <div>Assessment: <span className={out.assessment}>{out.assessment}</span></div>}
                {out?.status && <div>Status: <span className={out.status}>{out.status}</span>
                  {out?.confidence != null && <span> — Confidence: {Math.round(out.confidence * 100)}%</span>}</div>}
                {out?.reason && <div><small>{out.reason}</small></div>}
                {/* Evidence agent */}
                {out?.coverage && <div>Coverage: {out.coverage}</div>}
                {/* Devil's Advocate */}
                {Array.isArray(out?.risks) && <ul>{out.risks.map((r, k) => <li key={k}><small>{r}</small></li>)}</ul>}
                {/* Response Generator */}
                {out?.answer && <div><small>{out.answer}</small></div>}
                {out?.rationale && <div><small>Rationale: {out.rationale}</small></div>}
              </div>
            )) : <p><small>No agent breakdown available for this item.</small></p>}

            <h4>Final Answer</h4>
            <p>{selectedDetail.draft_response}</p>
            <div className="answer-source">
              {selectedDetail.answer_source === "llm" ? "GPT-drafted" : "Rule-based draft"}
            </div>
          </div>
        </div>}

        {page === "Human Review" && <>
          <h2>Human Review Queue</h2>
          {reviews.length === 0 && <p>No items waiting for review.</p>}
          {reviews.map(item => <section className="panel" key={item.id}>
            <b>{item.requirement}</b>
            <p>{item.edited_response || item.draft_response}</p>
            <div className="answer-source">
              {item.analysis?.answer_source === "llm" ? "GPT-drafted" : "Rule-based draft"}
            </div>
            <span className={`status ${item.status}`}>{item.status}</span>
            {item.status === "PENDING" && <div>
              <button onClick={() => decideReview(item.id, "APPROVED")}>Approve</button>
              <button onClick={() => decideReview(item.id, "EDITED")}>Edit</button>
              <button onClick={() => decideReview(item.id, "REJECTED")}>Reject</button>
            </div>}
          </section>)}
        </>}

        {page === "Final Bid" && <>
          <h2>Final Bid Pack</h2>
          {bids.length === 0 && <p>Analyze requirements and assemble a bid first.</p>}
          {bids.map(bid => <section className="panel" key={bid.id}>
            <h3>{bid.title}</h3>
            {Object.entries(bid.sections || {}).map(([section, items]) => <div key={section}>
              <h4>{section}</h4>
              {items.map((item, i) => <p key={i}><b>{item.requirement}</b><br/>{item.response}</p>)}
            </div>)}
            <div className="exports">
              <button onClick={() => window.open(`${API}/bids/${bid.id}/export/pdf`)}>Export PDF</button>
              <button onClick={() => window.open(`${API}/bids/${bid.id}/export/docx`)}>Export DOCX</button>
              <button onClick={() => window.open(`${API}/bids/${bid.id}/export/txt`)}>Export TXT</button>
            </div>
            <hr/>
            <b>Record outcome:</b>
            <button onClick={() => recordOutcome("WIN")}>WIN</button>
            <button onClick={() => recordOutcome("LOSS")}>LOSS</button>
          </section>)}
        </>}

        {page === "Knowledge Base" && <>
          <h2>Knowledge Base</h2>
          <section className="panel">
            <input className="search" value={knowledgeQuery} onChange={e => setKnowledgeQuery(e.target.value)}
              placeholder="Search certifications, policies, case studies, pricing..." />
            <button className="primary" onClick={searchKnowledge}>Search</button>
            <button onClick={async () => { await api("/knowledge-base/reindex", {method:"POST"}); setMessage("Knowledge Base re-indexed."); }}>Re-index</button>
          </section>
          {knowledgeResults.map((item, i) => <section className="panel" key={i}>
            <b>{item.source}</b> <span className="score">Score: {item.score}</span>
            <p>{item.text}</p>
            <small>{item.metadata?.category}</small>
          </section>)}
        </>}

        {page === "Bid Memory" && <>
          <h2>Bid Memory</h2>
          <p>WIN/LOSS outcomes become retrievable knowledge for future RFP analysis.</p>
          {memory.length === 0 && <p>No outcome memory recorded yet.</p>}
          {memory.map(item => <section className="panel" key={item.id}>
            <b>{item.rfp_name}</b> — <span className={`status ${item.outcome}`}>{item.outcome}</span>
            <p>{item.notes}</p>
            <ul>{(item.lessons || []).map((lesson, i) => <li key={i}>{lesson}</li>)}</ul>
          </section>)}
        </>}
      </main>
    </div>
  );
}

function Card({ title, value }) {
  return <div className="card"><small>{title}</small><strong>{value}</strong></div>;
}
