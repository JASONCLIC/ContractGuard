import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import client from "../api/client";

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
  while ((match = PLACEHOLDER_RE.exec(text || "")) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    if (start > last) parts.push({ type: "text", value: text.slice(last, start) });
    parts.push({ type: "token", value: match[1], full: match[0] });
    last = end;
  }
  if (last < (text || "").length) parts.push({ type: "text", value: text.slice(last) });

  return (
    <div
      style={{
        fontSize: 14,
        lineHeight: 1.75,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        color: "var(--gray)",
        margin: 0,
        fontFamily: "var(--font)",
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

export default function SharedViewPage() {
  const { token } = useParams();
  const [step, setStep]       = useState("loading"); // loading | password | content | error
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [content, setContent]  = useState(null);
  const [needsPassword, setNeedsPassword] = useState(false);

  const fetchContent = async (pwd = null) => {
    try {
      const params = pwd ? `?password=${encodeURIComponent(pwd)}` : "";
      const { data } = await client.get(`/share/${token}${params}`);
      setContent(data.data);
      setStep("content");
    } catch (e) {
      const code = e?.response?.data?.code;
      if (code === 4002) {
        setNeedsPassword(true);
        setStep("password");
        if (pwd !== null) setErrorMsg("Incorrect password. Please try again.");
      } else if (e?.response?.status === 410) {
        setErrorMsg("This share link has expired.");
        setStep("error");
      } else if (e?.response?.status === 429) {
        setErrorMsg("Access limit reached. This link is no longer valid.");
        setStep("error");
      } else {
        setErrorMsg("The link is invalid or has been revoked.");
        setStep("error");
      }
    }
  };

  useEffect(() => { fetchContent(); }, [token]);

  if (step === "loading") {
    return (
      <div className="loader-wrap" style={{ minHeight: "80vh" }}>
        <div className="spinner" />
        <span>Verifying link…</span>
      </div>
    );
  }

  if (step === "error") {
    return (
      <div style={{ minHeight: "80vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div className="card" style={{ textAlign: "center", padding: "48px 32px", maxWidth: 400 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔗</div>
          <h2 className="t-section" style={{ marginBottom: 10 }}>Link Unavailable</h2>
          <p className="t-body t-gray">{errorMsg}</p>
        </div>
      </div>
    );
  }

  if (step === "password") {
    return (
      <div style={{ minHeight: "80vh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div className="card" style={{ padding: 36, maxWidth: 380, width: "100%" }}>
          <div style={{ textAlign: "center", marginBottom: 24 }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>🔒</div>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>Password Required</h2>
            <p className="t-caption">This share link is password-protected</p>
          </div>
          <div className="stack stack-12">
            <input
              className="input"
              type="password"
              placeholder="Enter access password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && fetchContent(password)}
              autoFocus
            />
            {errorMsg && <div className="alert alert-error">{errorMsg}</div>}
            <button
              className="btn btn-primary w-full"
              onClick={() => fetchContent(password)}
              style={{ padding: 13, borderRadius: "var(--r-md)" }}
            >
              Access
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page page-narrow">
      <div className="stack stack-24">
        <div className="row" style={{ gap: 10 }}>
          <div style={{ width: 36, height: 36, background: "var(--blue)", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: 14, flexShrink: 0 }}>CG</div>
          <div>
            <h1 style={{ fontSize: 18, fontWeight: 700 }}>ContractGuard Shared Contract</h1>
            <p className="t-caption">The content below is a read-only, redacted version</p>
          </div>
        </div>

        <div className="alert alert-info">
          <span>🔒</span>
          <span>This page shows the redacted contract text with masked sensitive entities.</span>
        </div>

        {content?.redaction_summary?.length > 0 && (
          <div className="card" style={{ padding: "14px 16px" }}>
            <p className="t-caption" style={{ marginBottom: 8 }}>
              {content?.total_redactions || 0} items redacted
            </p>
            <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
              {content.redaction_summary.map((item) => {
                const style = REDACTION_STYLES[item.type] || { label: item.type, background: "#f3f4f6", color: "#4b5563" };
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
        )}

        <div className="card" style={{ padding: "20px 24px" }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Contract Text (Redacted)</h2>
          <RedactedTextBlock text={content?.text || "No content available"} />
        </div>
      </div>
    </div>
  );
}
