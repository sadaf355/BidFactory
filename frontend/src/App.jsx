import React, { useEffect, useMemo, useState } from "react";
import "./index.css";
import { SAMPLE_COMPANY_NAME, SAMPLE_KB_DOCS, SAMPLE_RFP_FILENAME, SAMPLE_RFP_REQUIREMENTS } from "./sampleData";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function api(path, options = {}) {
  const response = await fetch(API + path, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

const NAV = [
  { id: "dashboard", label: "Dashboard" },
  { id: "bids", label: "Bids" },
  { id: "newrfp", label: "New RFP" },
  { id: "knowledge", label: "Knowledge Base" },
  { id: "reviews", label: "Reviews" },
  { id: "memory", label: "Bid Memory" },
  { id: "settings", label: "Settings" },
];

// A "workspace" bundles one uploaded RFP with its extracted requirements,
// analysis results, and (once assembled) the resulting bid record.
function newWorkspace({ filename, requirements }) {
  return {
    id: crypto.randomUUID(),
    filename,
    uploadedAt: new Date().toISOString(),
    requirements,
    results: [],
    bid: null,
    outcome: null,
  };
}

function verdictClass(status) {
  if (status === "PASS") return "pass";
  if (status === "PARTIAL") return "partial";
  if (status === "MISSING" || status === "FAIL") return "missing";
  return "review"; // human_review / unknown
}

function verdictLabel(item) {
  if (item.human_review) return "NEEDS_HUMAN_REVIEW";
  return item.status || "UNKNOWN";
}

function ringGradient(counts) {
  const colors = { pass: "#2F6B4A", partial: "#A6642A", missing: "#A63B2E", review: "#35516B" };
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  let acc = 0;
  const stops = [];
  for (const key of ["pass", "partial", "missing", "review"]) {
    const val = counts[key];
    if (!val) continue;
    const start = (acc / total) * 360;
    const end = ((acc + val) / total) * 360;
    stops.push(`${colors[key]} ${start}deg ${end}deg`);
    acc += val;
  }
  if (!stops.length) stops.push("#DCD5C4 0deg 360deg");
  return `conic-gradient(${stops.join(",")})`;
}

function usePreferredTheme() {
  const [theme, setTheme] = useState(() => {
    const saved = typeof localStorage !== "undefined" && localStorage.getItem("bidfactory-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("bidfactory-theme", theme);
  }, [theme]);
  return [theme, setTheme];
}

export default function App() {
  const [theme, setTheme] = usePreferredTheme();
  const [page, setPage] = useState("dashboard");
  const [tab, setTab] = useState("overview");
  const [expandedRow, setExpandedRow] = useState(null);

  const [workspaces, setWorkspaces] = useState([]);
  const [activeId, setActiveId] = useState(null);

  const [pendingRequirements, setPendingRequirements] = useState([]);
  const [pendingFilename, setPendingFilename] = useState("");

  const [reviews, setReviews] = useState([]);
  const [bids, setBids] = useState([]);
  const [memory, setMemory] = useState([]);
  const [dashboard, setDashboard] = useState({});
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeResults, setKnowledgeResults] = useState([]);
  const [kbDocuments, setKbDocuments] = useState([]);
  const [kbCategories, setKbCategories] = useState([]);
  const [companyName, setCompanyName] = useState("Your Company");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const active = workspaces.find((w) => w.id === activeId) || null;

  const refresh = async () => {
    try {
      const [r, b, m, d, c] = await Promise.all([
        api("/reviews"),
        api("/bids"),
        api("/outcomes/memory"),
        api("/dashboard/summary"),
        api("/company"),
      ]);
      setReviews(r);
      setBids(b);
      setMemory(m);
      setDashboard(d);
      setCompanyName(c.name);
    } catch (_) {}
  };

  const loadKnowledgeMeta = async () => {
    try {
      const [docs, cats] = await Promise.all([
        api("/knowledge-base/documents"),
        api("/knowledge-base/categories"),
      ]);
      setKbDocuments(docs.documents || []);
      setKbCategories(cats.categories || []);
    } catch (_) {}
  };

  useEffect(() => { refresh(); loadKnowledgeMeta(); }, []);

  function goto(nextPage, opts = {}) {
    setPage(nextPage);
    setTab(opts.tab || "overview");
    setExpandedRow(null);
    if (opts.id) setActiveId(opts.id);
    setMessage("");
  }

  async function uploadRfp(file) {
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", file);
      const data = await api("/rfps/upload", { method: "POST", body: form });
      setPendingFilename(data.filename);
      setPendingRequirements(data.requirements || []);
      setMessage(`Extracted ${data.requirement_count} requirements from ${data.filename}.`);
    } catch (e) {
      setMessage("Upload failed: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runAnalysis() {
    const clean = pendingRequirements.map((x) => x.trim()).filter(Boolean);
    if (!clean.length) return setMessage("Add at least one requirement.");
    setBusy(true);
    try {
      const data = await api("/analysis/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements: clean }),
      });
      const ws = newWorkspace({
        filename: pendingFilename || "Untitled RFP",
        requirements: clean,
      });
      ws.results = data.results || [];
      setWorkspaces((prev) => [ws, ...prev]);
      setPendingFilename("");
      setPendingRequirements([]);
      goto("bidDetail", { id: ws.id, tab: "requirements" });
    } catch (e) {
      setMessage("Analysis failed: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendToReview(item) {
    await api("/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requirement: item.requirement,
        analysis: item,
        draft_response: item.draft_response,
      }),
    });
    await refresh();
    setMessage(`Sent "${item.requirement.slice(0, 60)}..." to review.`);
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
      body: JSON.stringify({ status, edited_response }),
    });
    refresh();
  }

  async function assembleBid(ws) {
    if (!ws.results.length) return;
    setBusy(true);
    try {
      const merged = ws.results.map((item) => {
        const review = reviews.find(
          (r) => r.requirement === item.requirement && ["APPROVED", "EDITED"].includes(r.status)
        );
        return review?.edited_response ? { ...item, edited_response: review.edited_response } : item;
      });
      const bid = await api("/bids/assemble", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_results: merged,
          company_name: companyName,
          title: `Bid Response — ${ws.filename}`,
        }),
      });
      setWorkspaces((prev) => prev.map((w) => (w.id === ws.id ? { ...w, bid } : w)));
      setBids((prev) => [...prev, bid]);
      setMessage("Final bid assembled.");
    } finally {
      setBusy(false);
    }
  }

  async function recordOutcome(ws, outcome) {
    await api("/outcomes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rfp_name: ws.filename,
        outcome,
        notes: "Outcome recorded from BidFactory workspace.",
        lessons: ["This win/loss result is now searchable as future Bid Memory."],
      }),
    });
    setWorkspaces((prev) => prev.map((w) => (w.id === ws.id ? { ...w, outcome } : w)));
    await refresh();
    goto("memory");
  }

  async function searchKnowledge() {
    if (!knowledgeQuery.trim()) return;
    const data = await api(`/knowledge-base/search?q=${encodeURIComponent(knowledgeQuery)}&top_k=10`);
    setKnowledgeResults(data.results || []);
  }

  async function uploadKnowledgeDocument(file, category) {
    const form = new FormData();
    form.append("file", file);
    form.append("category", category || "other");
    await api("/knowledge-base/upload", { method: "POST", body: form });
    await loadKnowledgeMeta();
  }

  async function handleKnowledgeUpload(file, category) {
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      await uploadKnowledgeDocument(file, category);
      setMessage(`Added "${file.name}" to the knowledge base.`);
    } catch (e) {
      setMessage("Upload failed: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteKnowledgeDocument(category, filename) {
    await api(`/knowledge-base/documents/${encodeURIComponent(category)}/${encodeURIComponent(filename)}`, {
      method: "DELETE",
    });
    await loadKnowledgeMeta();
  }

  async function saveCompanyName(name) {
    const data = await api("/company", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    setCompanyName(data.name);
    setMessage("Company name saved.");
  }

  async function seedDemoData() {
    const ok = window.confirm(
      `Load sample data? This sets your company name to "${SAMPLE_COMPANY_NAME}", adds ${SAMPLE_KB_DOCS.length} example knowledge-base documents, and runs one example RFP through the pipeline — a quick way to see BidFactory working before you add your own data.`
    );
    if (!ok) return;
    setBusy(true);
    setMessage("");
    try {
      await saveCompanyName(SAMPLE_COMPANY_NAME);
      for (const doc of SAMPLE_KB_DOCS) {
        const file = new File([doc.text], doc.filename, { type: "text/markdown" });
        await uploadKnowledgeDocument(file, doc.category);
      }
      const data = await api("/analysis/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requirements: SAMPLE_RFP_REQUIREMENTS }),
      });
      const ws = newWorkspace({ filename: SAMPLE_RFP_FILENAME, requirements: SAMPLE_RFP_REQUIREMENTS });
      ws.results = data.results || [];
      setWorkspaces((prev) => [ws, ...prev]);
      setMessage("Sample data loaded — this is what BidFactory looks like once your knowledge base and an RFP are in. Delete the sample documents from Knowledge Base whenever you're ready to add your own.");
      goto("bidDetail", { id: ws.id, tab: "requirements" });
    } catch (e) {
      setMessage("Couldn't load sample data: " + e.message);
    } finally {
      setBusy(false);
    }
  }

  const pendingReviewCount = reviews.filter((r) => r.status === "PENDING").length;
  const requirementTotal = workspaces.reduce((a, w) => a + w.results.length, 0);

  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <div className="brand-mark"><span className="dot" /><h1>BidFactory</h1></div>
          <p>Evidence-grounded RFP response copilot</p>
        </div>
        <nav>
          {NAV.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "active" : ""}
              onClick={() => goto(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="side-foot">
          <button
            className="theme-toggle"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle dark mode"
          >
            {theme === "dark" ? "Dark mode" : "Light mode"}
            <span className="track">
              <span className="knob">
                {theme === "dark" ? (
                  <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
                )}
              </span>
            </span>
          </button>
          <div className="status-line"><span className="pulse" /> BACKEND CONNECTED</div>
        </div>
      </aside>

      <main>
        <div className="topbar">
          <span className="crumb">{page === "bidDetail" ? "BID DETAILS" : page.toUpperCase()}</span>
          <span className="user-pill">DEMO USER</span>
        </div>

        <div className="content">
          {message && <div className="message">{message}</div>}

          {page === "dashboard" && (
            <Dashboard
              workspaces={workspaces}
              reviews={reviews}
              bids={bids}
              memory={memory}
              dashboard={dashboard}
              requirementTotal={requirementTotal}
              pendingReviewCount={pendingReviewCount}
              onOpen={(id) => goto("bidDetail", { id })}
              onViewAll={() => goto("bids")}
              onOpenSettings={() => goto("settings")}
            />
          )}

          {page === "bids" && (
            <Bids workspaces={workspaces} onOpen={(id) => goto("bidDetail", { id })} onNew={() => goto("newrfp")} />
          )}

          {page === "newrfp" && (
            <NewRfp
              busy={busy}
              filename={pendingFilename}
              requirements={pendingRequirements}
              onFile={uploadRfp}
              onChangeRequirements={setPendingRequirements}
              onRun={runAnalysis}
            />
          )}

          {page === "bidDetail" && active && (
            <BidDetail
              ws={active}
              tab={tab}
              setTab={setTab}
              expandedRow={expandedRow}
              setExpandedRow={setExpandedRow}
              busy={busy}
              onSendToReview={sendToReview}
              onAssemble={() => assembleBid(active)}
              onOutcome={(o) => recordOutcome(active, o)}
              apiBase={API}
            />
          )}
          {page === "bidDetail" && !active && (
            <p>Select a bid from the Bids page.</p>
          )}

          {page === "knowledge" && (
            <Knowledge
              query={knowledgeQuery}
              setQuery={setKnowledgeQuery}
              results={knowledgeResults}
              documents={kbDocuments}
              categories={kbCategories}
              busy={busy}
              onSearch={searchKnowledge}
              onUpload={handleKnowledgeUpload}
              onDelete={deleteKnowledgeDocument}
              onReindex={async () => {
                await api("/knowledge-base/reindex", { method: "POST" });
                await loadKnowledgeMeta();
                setMessage("Knowledge base re-indexed.");
              }}
            />
          )}

          {page === "reviews" && <Reviews reviews={reviews} onDecide={decideReview} />}

          {page === "memory" && <Memory memory={memory} />}

          {page === "settings" && (
            <Settings companyName={companyName} onSave={saveCompanyName} onSeed={seedDemoData} busy={busy} />
          )}
        </div>
      </main>
    </div>
  );
}

function Plate({ label, value, tone }) {
  return (
    <div className="plate">
      <div className="p-label">{label}</div>
      <div className={`p-value ${tone || ""}`}>{value}</div>
    </div>
  );
}

function Dashboard({ workspaces, reviews, bids, memory, dashboard, requirementTotal, pendingReviewCount, onOpen, onViewAll, onOpenSettings }) {
  return (
    <>
      <h2 className="page-title">Dashboard</h2>
      <p className="page-sub">One workspace per RFP — from upload to evidence-backed final bid.</p>
      <div className="plates">
        <Plate label="Active Bids" value={dashboard.bids ?? workspaces.length} />
        <Plate label="Requirements Analyzed" value={requirementTotal} />
        <Plate label="Pending Reviews" value={dashboard.reviews?.pending ?? pendingReviewCount} tone="warn" />
        <Plate label="Bid Memory" value={dashboard.bid_memory ?? memory.length} tone="accent" />
      </div>

      <section className="block">
        <div className="block-head">
          <h3>Recent Bids</h3>
          {workspaces.length > 0 && <a className="link" onClick={onViewAll}>View all →</a>}
        </div>
        {workspaces.length === 0 && (
          <p className="empty">
            No bids yet. Upload an RFP to start one, or{" "}
            <a className="link" onClick={onOpenSettings}>load sample data</a> to see it in action first.
          </p>
        )}
        {workspaces.slice(0, 5).map((w) => (
          <div className="bid-row" key={w.id} onClick={() => onOpen(w.id)}>
            <div>
              <div className="name">{w.filename}</div>
              <div className="sub">
                Uploaded {new Date(w.uploadedAt).toLocaleString()} · {w.results.length} requirements
              </div>
            </div>
            <div className="right">
              {w.outcome ? (
                <span className={`verdict ${verdictClass(w.outcome === "WIN" ? "PASS" : "MISSING")}`}>{w.outcome}</span>
              ) : w.bid ? (
                <span className="stamp completed">Completed</span>
              ) : (
                <span className="verdict review">In progress</span>
              )}
            </div>
          </div>
        ))}
      </section>
    </>
  );
}

function Bids({ workspaces, onOpen, onNew }) {
  return (
    <>
      <div className="block-head" style={{ marginBottom: 18 }}>
        <div>
          <h2 className="page-title">Bids</h2>
          <p className="page-sub" style={{ marginBottom: 0 }}>Every RFP you've run through the pipeline.</p>
        </div>
        <button className="btn btn-primary" onClick={onNew}>New RFP</button>
      </div>
      {workspaces.length === 0 && <p className="empty">No bids yet. Upload an RFP to start one.</p>}
      {workspaces.map((w) => (
        <div className="bid-row" key={w.id} onClick={() => onOpen(w.id)}>
          <div>
            <div className="name">{w.filename}</div>
            <div className="sub">
              Uploaded {new Date(w.uploadedAt).toLocaleString()} · {w.results.length} requirements
            </div>
          </div>
          <div className="right">
            {w.bid ? <span className="stamp completed">Completed</span> : <span className="verdict review">In progress</span>}
          </div>
        </div>
      ))}
    </>
  );
}

function NewRfp({ busy, filename, requirements, onFile, onChangeRequirements, onRun }) {
  return (
    <>
      <h2 className="page-title">New RFP</h2>
      <p className="page-sub">Upload a document or paste requirements directly — one per line.</p>
      <section className="block" style={{ marginTop: 0 }}>
        <div className="ring-plate stacked">
          <label className="dropzone">
            <input type="file" accept=".pdf,.docx,.txt,.md" onChange={(e) => onFile(e.target.files?.[0])} hidden />
            {filename ? (
              <span><b>{filename}</b> — {requirements.length} requirements extracted.</span>
            ) : (
              <span>Drop a PDF, DOCX, TXT or Markdown file here, or click to browse</span>
            )}
          </label>
          <textarea
            rows={8}
            value={requirements.join("\n")}
            onChange={(e) => onChangeRequirements(e.target.value.split("\n"))}
            placeholder={"Vendor must have ISO 27001 certification\nAll customer data in transit must be encrypted using TLS 1.3..."}
          />
          <div className="row-end">
            <button className="btn btn-primary" onClick={onRun} disabled={busy}>
              {busy ? "Running..." : "Run Analysis"}
            </button>
          </div>
        </div>
      </section>
    </>
  );
}

function BidDetail({ ws, tab, setTab, expandedRow, setExpandedRow, busy, onSendToReview, onAssemble, onOutcome, apiBase }) {
  const counts = useMemo(() => {
    const c = { pass: 0, partial: 0, missing: 0, review: 0 };
    ws.results.forEach((r) => { c[verdictClass(verdictLabel(r) === "NEEDS_HUMAN_REVIEW" ? "review" : r.status)]++; });
    return c;
  }, [ws.results]);
  const evidenceTotal = ws.results.reduce((a, r) => a + (r.evidence || []).length, 0);
  const pending = ws.results.filter((r) => r.human_review).length;
  const coveredPct = ws.results.length ? Math.round((counts.pass / ws.results.length) * 100) : 0;

  return (
    <>
      <div className="bid-header">
        <div>
          <h2 className="page-title">{ws.filename}</h2>
          <div className="meta">
            {ws.results.length} requirements · uploaded {new Date(ws.uploadedAt).toLocaleString()}
          </div>
        </div>
        <div className="bid-actions">
          {ws.bid ? <span className="stamp completed">Completed</span> : <span className="verdict review">In progress</span>}
          {ws.bid ? (
            <>
              <button className="btn btn-primary" onClick={() => window.open(`${apiBase}/bids/${ws.bid.id}/export/docx`)}>Export DOCX</button>
              <button className="btn btn-ghost" onClick={() => window.open(`${apiBase}/bids/${ws.bid.id}/export/pdf`)}>Export PDF</button>
              <button className="btn btn-ghost" onClick={() => onOutcome("WIN")}>Mark WIN</button>
              <button className="btn btn-ghost" onClick={() => onOutcome("LOSS")}>Mark LOSS</button>
            </>
          ) : (
            <button className="btn btn-primary" onClick={onAssemble} disabled={busy || !ws.results.length}>
              {busy ? "Assembling..." : "Assemble Final Bid"}
            </button>
          )}
        </div>
      </div>

      <div className="tabbar">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>Overview & Pipeline</button>
        <button className={tab === "requirements" ? "active" : ""} onClick={() => setTab("requirements")}>Requirements & Evidence</button>
        <button className={tab === "responses" ? "active" : ""} onClick={() => setTab("responses")}>AI Responses</button>
      </div>

      {tab === "overview" && (
        <>
          <div className="plates">
            <Plate label="Requirements" value={ws.results.length} />
            <Plate label="Covered" value={counts.pass} tone={counts.pass ? "accent" : ""} />
            <Plate label="Evidence Retrieved" value={evidenceTotal} />
            <Plate label="Reviews Pending" value={pending} tone="warn" />
          </div>

          <section className="block">
            <div className="block-head"><h3>Compliance Breakdown</h3></div>
            <div className="ring-plate">
              <div className="ring-wrap">
                <div className="ring-fill" style={{ background: ringGradient(counts) }} />
                <div className="ring-center"><b>{coveredPct}%</b><span>Covered</span></div>
              </div>
              <div className="legend">
                <div className="row"><span className="swatch" style={{ background: "#2F6B4A" }} />Pass<span className="count">{counts.pass}</span></div>
                <div className="row"><span className="swatch" style={{ background: "#A6642A" }} />Partial<span className="count">{counts.partial}</span></div>
                <div className="row"><span className="swatch" style={{ background: "#A63B2E" }} />Missing<span className="count">{counts.missing}</span></div>
                <div className="row"><span className="swatch" style={{ background: "#35516B" }} />Needs Review<span className="count">{counts.review}</span></div>
              </div>
            </div>
          </section>

          <section className="block">
            <div className="block-head"><h3>Pipeline</h3></div>
            <div className="pipeline">
              {["Upload", "Extract", "Retrieve", "Agents", "Validate", "Human Gate"].map((s, i) => (
                <div className={`pipe-step ${i < 5 ? "done" : ""}`} key={s}>
                  <div className="n">{String(i + 1).padStart(2, "0")}</div>
                  <div className="t">{s}</div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {tab === "requirements" && (
        <table>
          <thead>
            <tr><th style={{ width: "38%" }}>Requirement</th><th>Evidence</th><th>Compliance / Confidence</th><th /></tr>
          </thead>
          <tbody>
            {ws.results.map((item, i) => (
              <React.Fragment key={i}>
                <tr className="req-row" onClick={() => setExpandedRow(expandedRow === i ? null : i)}>
                  <td><div className="req-title">{item.requirement}</div></td>
                  <td><span className="ev-count">{(item.evidence || []).length} items</span></td>
                  <td>
                    <span className={`verdict ${verdictClass(item.human_review ? "review" : item.status)}`}>
                      {verdictLabel(item)}
                    </span>
                    {typeof item.confidence === "number" && (
                      <div className="conf">Conf: {Math.round(item.confidence * 100)}%</div>
                    )}
                  </td>
                  <td>
                    {item.human_review && (
                      <button className="btn btn-ghost btn-sm" onClick={(e) => { e.stopPropagation(); onSendToReview(item); }}>
                        Send to Review
                      </button>
                    )}
                  </td>
                </tr>
                {expandedRow === i && (
                  <tr className="ev-panel">
                    <td colSpan={4}>
                      {(item.evidence || []).slice(0, 5).map((e, j) => (
                        <div className="ev-item" key={j}>
                          <div className="src">{e.source}</div>
                          <p>{(e.text || "").slice(0, 300)}</p>
                        </div>
                      ))}
                      {(!item.evidence || item.evidence.length === 0) && (
                        <p className="empty" style={{ margin: "10px 0" }}>No supporting evidence found in the knowledge base.</p>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}

      {tab === "responses" && (
        <>
          {ws.results.map((item, i) => (
            <div className="resp-card" key={i}>
              <div className="resp-head">
                <div className="resp-req">{item.requirement}</div>
                <span className={`verdict ${verdictClass(item.human_review ? "review" : item.status)}`}>{verdictLabel(item)}</span>
              </div>
              {item.draft_response ? (
                <div className="resp-text">{item.draft_response}</div>
              ) : (
                <div className="resp-text no-evidence">No answer drafted — insufficient evidence to support a claim.</div>
              )}
              <div className="agent-row">
                <span className="agent-chip"><b>Answer Source</b>{item.answer_source === "llm" ? "GPT-drafted" : "Rule-based draft"}</span>
                {item.reason && <span className="agent-chip"><b>Compliance Reasoning</b>{item.reason}</span>}
              </div>
              {item.human_review && (
                <div className="resp-actions">
                  <button className="btn btn-primary btn-sm" onClick={() => onSendToReview(item)}>Send to Review</button>
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </>
  );
}

function Knowledge({ query, setQuery, results, documents, categories, busy, onSearch, onUpload, onDelete, onReindex }) {
  const [category, setCategory] = useState(categories[0] || "other");
  useEffect(() => { if (categories.length && !categories.includes(category)) setCategory(categories[0]); }, [categories]);

  return (
    <>
      <h2 className="page-title">Knowledge Base</h2>
      <p className="page-sub">Your own certifications, policies, case studies and pricing — the evidence every answer must trace back to. Empty until you add documents below.</p>

      <section className="block" style={{ marginTop: 0 }}>
        <div className="ring-plate stacked">
          <label className="dropzone">
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              hidden
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f, category); e.target.value = ""; }}
            />
            {busy ? "Uploading..." : "Drop a PDF, DOCX, TXT or Markdown file here, or click to browse"}
          </label>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>Category:</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ padding: "8px 12px", borderRadius: "var(--r-pill)", border: "1px solid var(--line)", background: "var(--surface)", color: "var(--ink)", fontFamily: "inherit", fontSize: 13 }}>
              {(categories.length ? categories : ["other"]).map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
            </select>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="block-head"><h3>Documents ({documents.length})</h3></div>
        {documents.length === 0 && <p className="empty">No documents uploaded yet.</p>}
        {documents.map((d) => (
          <div className="kb-card" key={`${d.category}/${d.filename}`}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
              <div>
                <div className="tag">{d.category.replace(/_/g, " ")}</div>
                <h4>{d.filename}</h4>
                <p>{(d.size / 1024).toFixed(1)} KB</p>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={() => onDelete(d.category, d.filename)}>Delete</button>
            </div>
          </div>
        ))}
      </section>

      <section className="block">
        <div className="block-head"><h3>Search</h3></div>
        <div className="search-row">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search certifications, policies, case studies, pricing..." />
          <button className="btn btn-primary" onClick={onSearch}>Search</button>
          <button className="btn btn-ghost" onClick={onReindex}>Re-index</button>
        </div>
        {results.map((item, i) => (
          <div className="kb-card" key={i}>
            <div className="tag">{item.metadata?.category || "Document"}</div>
            <h4>{item.source}</h4>
            <p>{item.text}</p>
          </div>
        ))}
      </section>
    </>
  );
}

function Settings({ companyName, onSave, onSeed, busy }) {
  const [value, setValue] = useState(companyName);
  useEffect(() => setValue(companyName), [companyName]);
  const dirty = value.trim() && value !== companyName;

  return (
    <>
      <h2 className="page-title">Settings</h2>
      <p className="page-sub">Your company's identity — used in generated answers and the assembled bid document.</p>
      <div className="ring-plate stacked" style={{ maxWidth: 480 }}>
        <div>
          <div className="p-label" style={{ marginBottom: 8 }}>Company name</div>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. Acme Corp"
            style={{ width: "100%", padding: "11px 16px", border: "1px solid var(--line)", borderRadius: "var(--r-pill)", fontFamily: "inherit", fontSize: 13.5, background: "var(--surface)", color: "var(--ink)" }}
          />
        </div>
        <div className="row-end">
          <button className="btn btn-primary" disabled={!dirty} onClick={() => onSave(value.trim())}>Save</button>
        </div>
      </div>

      <section className="block">
        <div className="block-head"><h3>Try it with sample data</h3></div>
        <div className="ring-plate stacked" style={{ maxWidth: 480 }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--ink-soft)", lineHeight: 1.6 }}>
            The app ships empty — no company, no knowledge base, no RFP. If you'd
            rather see it working before setting up your own data, this loads a
            small fictional company ("Acme Cloud Solutions") with a few example
            documents and runs one example RFP through the full pipeline. Delete
            the sample documents from Knowledge Base at any time.
          </p>
          <div className="row-end">
            <button className="btn btn-ghost" onClick={onSeed} disabled={busy}>
              {busy ? "Loading..." : "Load Sample Data"}
            </button>
          </div>
        </div>
      </section>
    </>
  );
}

function Reviews({ reviews, onDecide }) {
  return (
    <>
      <h2 className="page-title">Reviews</h2>
      <p className="page-sub">Anything the agents couldn't confirm on their own waits here.</p>
      {reviews.length === 0 && <p className="empty">No items waiting for review.</p>}
      {reviews.map((item) => (
        <div className="resp-card" key={item.id}>
          <div className="resp-head">
            <div className="resp-req">{item.requirement}</div>
            <span className={`verdict ${verdictClass(item.status === "APPROVED" ? "PASS" : item.status === "REJECTED" ? "MISSING" : "PARTIAL")}`}>
              {item.status}
            </span>
          </div>
          <div className="resp-text">{item.edited_response || item.draft_response}</div>
          <div className="agent-row">
            <span className="agent-chip"><b>Answer Source</b>{item.analysis?.answer_source === "llm" ? "GPT-drafted" : "Rule-based draft"}</span>
          </div>
          {item.status === "PENDING" && (
            <div className="resp-actions">
              <button className="btn btn-primary btn-sm" onClick={() => onDecide(item.id, "APPROVED")}>Approve</button>
              <button className="btn btn-ghost btn-sm" onClick={() => onDecide(item.id, "EDITED")}>Edit</button>
              <button className="btn btn-ghost btn-sm" onClick={() => onDecide(item.id, "REJECTED")}>Reject</button>
            </div>
          )}
        </div>
      ))}
    </>
  );
}

function Memory({ memory }) {
  return (
    <>
      <h2 className="page-title">Bid Memory</h2>
      <p className="page-sub">WIN/LOSS outcomes become searchable evidence for future RFPs.</p>
      {memory.length === 0 && <p className="empty">No outcome memory recorded yet.</p>}
      {memory.map((item) => (
        <div className="kb-card" key={item.id}>
          <div className="tag" style={{ color: item.outcome === "WIN" ? "var(--pass)" : "var(--missing)" }}>{item.outcome}</div>
          <h4>{item.rfp_name}</h4>
          <p>{item.notes}</p>
          {(item.lessons || []).length > 0 && (
            <ul className="lessons">
              {item.lessons.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
          )}
        </div>
      ))}
    </>
  );
}
