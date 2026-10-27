import { useEffect, useMemo, useState } from "react";

import ClauseCard from "../components/ClauseCard";
import RiskBadge from "../components/RiskBadge";
import useAnalysis from "../hooks/useAnalysis";
import useContractStore from "../store/useContractStore";
import client from "../api/client";

const KEY_LABELS = {
  contract_name:          "Contract Type",
  party_a:                "Party A (Employer)",
  party_b:                "Party B (Employee)",
  salary_amount:          "Salary Amount",
  payment_cycle:          "Payment Cycle",
  job_title:              "Job Title",
  work_location:          "Work Location",
  probation:              "Probation Period",
  contract_term:          "Contract Term",
  termination_conditions: "Termination Conditions",
  breach_liability:       "Breach Liability",
  dispute_resolution:     "Dispute Resolution",
};

/* ── Summary ── */
function SummaryView({ summary }) {
  const entries = Object.entries(summary || {});
  if (!entries.length) {
    return <div className="loader-wrap"><p className="t-gray">No summary data available</p></div>;
  }
  return (
    <div className="info-grid">
      {entries.map(([key, value]) => (
        <div key={key} className="info-item">
          <div className="info-item-label">{KEY_LABELS[key] || key}</div>
          <div className="info-item-value">{String(value || "Not identified")}</div>
        </div>
      ))}
    </div>
  );
}

/* ── Structure ── */
function StructureView({ clauses }) {
  const [keyword, setKeyword] = useState("");
  const filtered = useMemo(() => {
    if (!keyword) return clauses || [];
    return (clauses || []).filter(
      (c) =>
        c.content?.includes(keyword) ||
        c.heading?.includes(keyword) ||
        c.category?.includes(keyword)
    );
  }, [clauses, keyword]);

  if (!clauses?.length) {
    return <div className="loader-wrap"><p className="t-gray">No clause data available</p></div>;
  }
  return (
    <div className="stack stack-16">
      <input
        className="input"
        placeholder="Search clauses (keyword, clause name…)"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
      />
      <div className="stack stack-10" style={{ gap: 10 }}>
        {filtered.map((clause) => (
          <ClauseCard key={clause.index_num} clause={clause} />
        ))}
      </div>
    </div>
  );
}

/* ── Risks ── */
function RiskView({ risks, clauses }) {
  const [level, setLevel] = useState("all");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 3;
  const LEVEL_ORDER = { high: 0, medium: 1, low: 2 };

  const clauseMap = useMemo(() => {
    const map = new Map();
    (clauses || []).forEach((c) => map.set(c.index_num, c));
    return map;
  }, [clauses]);

  const filtered = useMemo(() => {
    const source = level === "all"
      ? [...(risks || [])]
      : (risks || []).filter((r) => r.risk_level === level);
    source.sort((a, b) => {
      const la = LEVEL_ORDER[a.risk_level] ?? 99;
      const lb = LEVEL_ORDER[b.risk_level] ?? 99;
      if (la !== lb) return la - lb;
      return (a.index_num ?? 0) - (b.index_num ?? 0);
    });
    return source;
  }, [risks, level]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, currentPage]);
  const pageButtons = useMemo(() => {
    const pages = [];
    if (totalPages <= 7) {
      for (let p = 1; p <= totalPages; p += 1) pages.push(p);
      return pages;
    }

    pages.push(1);
    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);

    if (start > 2) pages.push("left-ellipsis");
    for (let p = start; p <= end; p += 1) pages.push(p);
    if (end < totalPages - 1) pages.push("right-ellipsis");

    pages.push(totalPages);
    return pages;
  }, [currentPage, totalPages]);

  useEffect(() => {
    setPage(1);
  }, [level]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  if (!risks?.length) {
    return (
      <div className="loader-wrap">
        <div style={{ fontSize: 40 }}>✓</div>
        <p className="t-gray">No risk clauses detected</p>
      </div>
    );
  }

  const FILTERS = [
    { v: "all",    label: "All" },
    { v: "high",   label: "High Risk" },
    { v: "medium", label: "Medium Risk" },
    { v: "low",    label: "Low Risk" },
  ];

  return (
    <div className="stack stack-16">
      {/* Level filter */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {FILTERS.map(({ v, label }) => (
          <button
            key={v}
            type="button"
            onClick={() => setLevel(v)}
            style={{
              padding: "6px 16px",
              borderRadius: "var(--r-pill)",
              border: level === v ? "2px solid var(--blue)" : "2px solid var(--border)",
              background: level === v ? "rgba(0,113,227,0.06)" : "transparent",
              color: level === v ? "var(--blue)" : "var(--gray)",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
              fontFamily: "var(--font)",
              transition: "all 0.15s ease",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Risk cards */}
      <div className="stack" style={{ gap: 10 }}>
        {pageItems.map((risk, i) => (
          <div
            key={i}
            style={{
              background: "var(--white)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-lg)",
              padding: "20px 22px",
              boxShadow: "0 6px 20px rgba(0,0,0,0.04)",
              borderLeft: `4px solid ${
                risk.risk_level === "high" ? "#ff3b30"
                : risk.risk_level === "medium" ? "#ff9500"
                : "#007aff"
              }`,
            }}
          >
            <div className="row" style={{ gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
              <RiskBadge level={risk.risk_level} />
              <span style={{ fontWeight: 600, fontSize: 15 }}>{risk.risk_type}</span>
              {clauseMap.get(risk.index_num) && (
                <span className="t-caption" style={{ marginLeft: "auto" }}>
                  {clauseMap.get(risk.index_num).heading}
                </span>
              )}
            </div>
            {risk.llm_explanation ? (
              <>
                <div
                  style={{
                    background: "linear-gradient(180deg, #f2f8ff 0%, #eef6ff 100%)",
                    border: "1px solid #d8e9ff",
                    borderLeft: "4px solid #2f7cf6",
                    borderRadius: "12px",
                    padding: "12px 14px",
                    marginBottom: 12,
                  }}
                >
                  <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <p className="t-caption" style={{ fontWeight: 800, color: "#245fbf", letterSpacing: 0.2 }}>
                      Interpretion
                    </p>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#245fbf",
                        background: "#deecff",
                        borderRadius: "999px",
                        padding: "2px 8px",
                      }}
                    >
                      PRIORITY
                    </span>
                  </div>
                  <p className="t-body" style={{ lineHeight: 1.78, color: "#163b74", fontWeight: 500 }}>
                    {risk.llm_explanation}
                  </p>
                </div>
                <div style={{ borderTop: "1px dashed var(--border)", margin: "12px 0 10px" }} />
                <p className="t-caption" style={{ fontWeight: 700, marginBottom: 6, color: "var(--gray)" }}>Original Clause</p>
                <p
                  className="t-caption"
                  style={{
                    fontStyle: "italic",
                    lineHeight: 1.65,
                    background: "#f8f8fa",
                    border: "1px solid var(--border)",
                    borderRadius: 10,
                    padding: "10px 12px",
                  }}
                >
                  {risk.evidence_sentence}
                </p>
              </>
            ) : (
              <>
                <div
                  style={{
                    background: "#fff9ef",
                    border: "1px solid #ffe2b0",
                    borderLeft: "4px solid #ff9500",
                    borderRadius: "12px",
                    padding: "12px 14px",
                    marginBottom: 10,
                  }}
                >
                  <p className="t-caption" style={{ fontWeight: 700, color: "#b36200", marginBottom: 6 }}>
                    Static Analysis (Fallback)
                  </p>
                  <p className="t-body" style={{ marginBottom: 0, lineHeight: 1.72, color: "#7a4a00" }}>{risk.explanation}</p>
                </div>
                <p className="t-caption" style={{ fontStyle: "italic", lineHeight: 1.6, color: "var(--gray)" }}>
                  {risk.evidence_sentence}
                </p>
              </>
            )}
          </div>
        ))}
      </div>

      {filtered.length > PAGE_SIZE && (
        <div className="row-between" style={{ marginTop: 4, flexWrap: "wrap", gap: 10 }}>
          <p className="t-caption">
            Page {currentPage} / {totalPages} · Showing {(currentPage - 1) * PAGE_SIZE + 1}-
            {Math.min(currentPage * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-ghost"
              style={{ padding: "6px 12px", fontSize: 13 }}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              Prev
            </button>
            {pageButtons.map((item) =>
              typeof item === "number" ? (
                <button
                  key={item}
                  type="button"
                  onClick={() => setPage(item)}
                  style={{
                    minWidth: 32,
                    height: 32,
                    borderRadius: "var(--r-pill)",
                    border: item === currentPage ? "2px solid var(--blue)" : "1px solid var(--border)",
                    background: item === currentPage ? "rgba(0,113,227,0.06)" : "var(--white)",
                    color: item === currentPage ? "var(--blue)" : "var(--gray)",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {item}
                </button>
              ) : (
                <span key={item} className="t-caption" style={{ padding: "0 2px" }}>
                  ...
                </span>
              )
            )}
            <button
              type="button"
              className="btn btn-ghost"
              style={{ padding: "6px 12px", fontSize: 13 }}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Missing ── */
function MissingView({ missing }) {
  if (!missing?.length) {
    return (
      <div className="loader-wrap">
        <div style={{ fontSize: 40 }}>✓</div>
        <p className="t-gray">All key clauses are covered</p>
      </div>
    );
  }
  return (
    <div className="stack" style={{ gap: 10 }}>
      {missing.map((item, i) => (
        <div
          key={i}
          style={{
            background: "var(--white)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-lg)",
            padding: "20px 22px",
            borderLeft: "4px solid #ff9500",
          }}
        >
          <div className="row" style={{ gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 15, fontWeight: 600 }}>{item.item_name}</span>
            <span className="pill pill-medium">Possibly Missing</span>
          </div>
          <p className="t-body" style={{ marginBottom: 6 }}>{item.description}</p>
          <p className="t-caption" style={{ color: "#b36200" }}>{item.potential_risk}</p>
        </div>
      ))}
    </div>
  );
}

/* ── Main page ── */
/* ── Desensitize ── */
const REDACTION_STYLES = {
  EMPLOYER: { label: "Employer", background: "#eaf2ff", color: "#245fbf" },
  EMPLOYEE: { label: "Employee", background: "#eaf2ff", color: "#245fbf" },
  EMAIL: { label: "Email", background: "#fff2e2", color: "#b36200" },
  PHONE: { label: "Phone", background: "#fff2e2", color: "#b36200" },
  SSN: { label: "SSN", background: "#ffe9e7", color: "#b42318" },
  NIN: { label: "NIN", background: "#ffe9e7", color: "#b42318" },
  PASSPORT: { label: "Passport", background: "#ffe9e7", color: "#b42318" },
  SALARY: { label: "Salary", background: "#e8f7ec", color: "#1a7f4b" },
  "BANK ACCOUNT": { label: "Bank Account", background: "#e8f7ec", color: "#1a7f4b" },
  ADDRESS: { label: "Address", background: "#f3f4f6", color: "#4b5563" },
  "WORK LOCATION": { label: "Work Location", background: "#f3f4f6", color: "#4b5563" },
  "DATE OF BIRTH": { label: "Date of Birth", background: "#f3f4f6", color: "#4b5563" },
};

const PLACEHOLDER_RE = /\[([A-Z ]+)\]/g;

function RedactedTextBlock({ text }) {
  const parts = [];
  let last = 0;
  let match;
  while ((match = PLACEHOLDER_RE.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    if (start > last) parts.push({ type: "text", value: text.slice(last, start) });
    parts.push({ type: "token", value: match[1], full: match[0] });
    last = end;
  }
  if (last < text.length) parts.push({ type: "text", value: text.slice(last) });

  return (
    <div
      className="input textarea"
      style={{
        borderRadius: "var(--r-lg)",
        background: "#f9fafb",
        color: "var(--gray)",
        cursor: "text",
        minHeight: 300,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        lineHeight: 1.75,
      }}
    >
      {parts.map((part, idx) => {
        if (part.type === "text") return <span key={idx}>{part.value}</span>;
        const style = REDACTION_STYLES[part.value] || { label: part.value, background: "#f3f4f6", color: "#4b5563" };
        return (
          <span
            key={idx}
            style={{
              display: "inline-block",
              padding: "1px 8px",
              margin: "0 2px",
              borderRadius: 999,
              background: style.background,
              color: style.color,
              fontSize: 12,
              fontWeight: 700,
              verticalAlign: "baseline",
            }}
            title={style.label}
          >
            {part.full}
          </span>
        );
      })}
    </div>
  );
}

function DesensitizeView({ contractId }) {
  const [text, setText] = useState(null);
  const [summary, setSummary] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await client.get(`/export/${contractId}/desensitized`);
      setText(data.data.desensitized_text);
      setSummary(data.data.redaction_summary || []);
      setTotal(data.data.total_redactions || 0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [contractId]);

  const copy = () => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="loader-wrap">
        <div className="spinner" />
        <span>Preparing redacted content…</span>
      </div>
    );
  }

  if (!text) {
    return <div className="loader-wrap"><p className="t-gray">No redacted content available</p></div>;
  }

  return (
    <div className="stack stack-12">
      <div className="row-between">
        <p className="t-caption">Sensitive info is redacted and safe to share.</p>
        <button className="btn btn-ghost" style={{ padding: "6px 16px", fontSize: 13 }} onClick={copy}>
          {copied ? "✓ Copied" : "Copy Text"}
        </button>
      </div>
      <div className="card" style={{ padding: "14px 16px", border: "1px dashed var(--border)" }}>
        <p className="t-caption" style={{ marginBottom: 8 }}>
          {total > 0 ? `${total} items redacted` : "No sensitive entities detected"}
        </p>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          {summary.map((item) => {
            const style = REDACTION_STYLES[item.type] || { background: "#f3f4f6", color: "#4b5563", label: item.type };
            return (
              <span
                key={item.type}
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  padding: "4px 10px",
                  borderRadius: 999,
                  background: style.background,
                  color: style.color,
                }}
              >
                {style.label}: {item.count}
              </span>
            );
          })}
        </div>
      </div>
      <RedactedTextBlock text={text} />
    </div>
  );
}

const TABS = [
  { key: "summary",     label: "Key Info" },
  { key: "structure",   label: "Clause Structure" },
  { key: "risks",       label: "Risk Clauses" },
  { key: "missing",     label: "Missing Items" },
  { key: "desensitize", label: "Redacted Text" },
];

export default function AnalysisPage() {
  const contractId = useContractStore((s) => s.contractId);
  const { structure, summary, risks, missing } = useAnalysis(contractId);
  const [tab, setTab] = useState("summary");
  const [exporting, setExporting] = useState(false);

  const exportReport = async () => {
    setExporting(true);
    try {
      const { data } = await client.post(`/export/${contractId}/pdf`);
      const jobId = data.data.job_id;
      const resp = await client.get(`/export/${contractId}/pdf/${jobId}`, {
        responseType: "blob",
      });
      // 从响应头读取服务器给定的文件名（.pdf 或降级时的 .txt）
      const disposition = resp.headers?.["content-disposition"] ?? "";
      const nameMatch = disposition.match(/filename[^;=\n]*=([^;\n"]+)/);
      const filename = nameMatch
        ? nameMatch[1].trim().replace(/^["']|["']$/g, "")
        : `ContractGuard_Report_${contractId}.pdf`;
      const mimeType = resp.headers?.["content-type"] ?? "application/pdf";
      const url = URL.createObjectURL(new Blob([resp.data], { type: mimeType }));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Export failed. Please try again later.");
    } finally {
      setExporting(false);
    }
  };

  if (!contractId) {
    return (
      <div className="page" style={{ maxWidth: 860 }}>
        <div className="alert alert-info">
          Please upload or paste a contract first before viewing analysis results.
        </div>
      </div>
    );
  }

  const loading =
    structure.isLoading || summary.isLoading || risks.isLoading || missing.isLoading;
  const hasError =
    structure.error || summary.error || risks.error || missing.error;

  if (loading) {
    return (
      <div className="page">
        <div className="loader-wrap">
          <div className="spinner" />
          <span>Loading analysis results…</span>
        </div>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="page" style={{ maxWidth: 860 }}>
        <div className="alert alert-error">Failed to load analysis results. Please try again later.</div>
      </div>
    );
  }

  const riskCount    = (risks.data   || []).length;
  const missingCount = (missing.data || []).length;

  return (
    <div className="page" style={{ maxWidth: 860 }}>
      {/* Page header */}
      <div className="row-between" style={{ marginBottom: 28, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 className="t-title" style={{ marginBottom: 4 }}>Analysis Results</h1>
          <p className="t-caption">Contract ID #{contractId}</p>
        </div>
        <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          <button
            className="btn btn-ghost"
            style={{ padding: "8px 18px", fontSize: 14 }}
            onClick={exportReport}
            disabled={exporting}
          >
            {exporting ? "Exporting…" : "↓ Export Report"}
          </button>
          {riskCount > 0 && (
            <span className="pill pill-high" style={{ fontSize: 13 }}>
              ⚠ {riskCount} {riskCount === 1 ? "Risk" : "Risks"}
            </span>
          )}
          {missingCount > 0 && (
            <span className="pill pill-medium" style={{ fontSize: 13 }}>
              ! {missingCount} {missingCount === 1 ? "Missing Item" : "Missing Items"}
            </span>
          )}
          {riskCount === 0 && missingCount === 0 && (
            <span className="pill" style={{ fontSize: 13, background: "#f0faf4", color: "#1a7f4b" }}>
              ✓ No Issues Found
            </span>
          )}
        </div>
      </div>

      {/* Pill tab bar */}
      <div className="tab-bar" style={{ marginBottom: 24 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`tab-item${tab === t.key ? " active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
            {t.key === "risks" && riskCount > 0 && (
              <span
                style={{
                  background: "#ff3b30",
                  color: "white",
                  borderRadius: "var(--r-pill)",
                  padding: "1px 6px",
                  fontSize: 10,
                  fontWeight: 700,
                  lineHeight: 1.6,
                }}
              >
                {riskCount}
              </span>
            )}
            {t.key === "missing" && missingCount > 0 && (
              <span
                style={{
                  background: "#ff9500",
                  color: "white",
                  borderRadius: "var(--r-pill)",
                  padding: "1px 6px",
                  fontSize: 10,
                  fontWeight: 700,
                  lineHeight: 1.6,
                }}
              >
                {missingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "summary"     && <SummaryView     summary={summary.data || {}} />}
      {tab === "structure"   && <StructureView   clauses={structure.data || []} />}
      {tab === "risks"       && <RiskView        risks={risks.data || []} clauses={structure.data || []} />}
      {tab === "missing"     && <MissingView     missing={missing.data || []} />}
      {tab === "desensitize" && <DesensitizeView contractId={contractId} />}
    </div>
  );
}
