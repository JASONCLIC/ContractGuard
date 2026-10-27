import { useState } from "react";

import client from "../api/client";
import useContractStore from "../store/useContractStore";

const EXPIRY_OPTIONS = [
  { value: 24,  label: "24 Hours" },
  { value: 72,  label: "3 Days" },
  { value: 168, label: "7 Days" },
];

export default function SharePage() {
  const contractId = useContractStore((s) => s.contractId);
  const [password, setPassword]     = useState("");
  const [usePassword, setUsePassword] = useState(false);
  const [expiresHours, setExpiresHours] = useState(72);
  const [loading, setLoading]       = useState(false);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState("");
  const [copied, setCopied]         = useState(false);

  const create = async () => {
    setLoading(true);
    setError("");
    try {
      const { data } = await client.post("/share/create", {
        contract_id: contractId,
        password: usePassword && password ? password : null,
        expires_hours: expiresHours,
      });
      const token = data.data.token;
      const shareUrl = `${window.location.origin}/shared/${token}`;
      setResult({ ...data.data, shareUrl });
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to create link. Please ensure the contract has been analysed first.");
    } finally {
      setLoading(false);
    }
  };

  const copy = () => {
    navigator.clipboard.writeText(result.shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="page page-narrow">
      <div className="stack stack-32">
        <div>
          <h1 className="t-title" style={{marginBottom: 8}}>Secure Share</h1>
          <p className="t-body t-gray">
            Generate a redacted, read-only share link with optional password protection and expiry to keep your contract
            private.
          </p>
        </div>

        {!contractId && (
            <div className="alert alert-info">Please upload and analyse a contract on the Contract Analysis page before
              using the share feature.</div>
        )}

        {contractId && !result && (
            <div className="card stack stack-20" style={{gap: 20}}>
              <div>
                <p style={{fontSize: 13, color: "var(--gray)", marginBottom: 8}}>
                  Current Contract ID: <strong style={{color: "var(--dark)"}}>#{contractId}</strong>
                </p>
                <p className="t-caption">The shared content will be a redacted version of the contract — sensitive
                  information is replaced automatically.</p>
              </div>

              <div className="divider"/>

              {/* Expiry */}
              <div>
                <label className="input-label">Expiry</label>
                <div style={{display: "flex", gap: 8}}>
                  {EXPIRY_OPTIONS.map((o) => (
                      <button
                          key={o.value}
                          type="button"
                          onClick={() => setExpiresHours(o.value)}
                          style={{
                            flex: 1,
                            padding: "9px 0",
                            borderRadius: "var(--r-md)",
                            border: expiresHours === o.value
                                ? "2px solid var(--blue)"
                                : "2px solid var(--border)",
                            background: expiresHours === o.value
                                ? "rgba(0,113,227,0.06)"
                                : "transparent",
                            color: expiresHours === o.value ? "var(--blue)" : "var(--gray)",
                            fontSize: 14,
                            fontWeight: 500,
                            cursor: "pointer",
                            fontFamily: "var(--font)",
                            transition: "all 0.15s ease",
                          }}
                      >
                        {o.label}
                      </button>
                  ))}
                </div>
              </div>

              {/* Password toggle */}
              <div>
                <div className="row" style={{gap: 10, marginBottom: usePassword ? 10 : 0}}>
                  <label
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        cursor: "pointer",
                        fontSize: 14,
                        fontWeight: 500,
                      }}
                  >
                    <input
                        type="checkbox"
                        checked={usePassword}
                        onChange={(e) => setUsePassword(e.target.checked)}
                        style={{width: 16, height: 16, accentColor: "var(--blue)"}}
                    />
                    Set Access Password
                  </label>
                </div>
                {usePassword && (
                    <input
                        className="input"
                        type="password"
                        placeholder="Enter share password (leave blank for no password)"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        style={{marginTop: 10}}
                    />
                )}
              </div>

              {error && <div className="alert alert-error">{error}</div>}

              <button
                  className="btn btn-primary"
                  onClick={create}
                  disabled={loading}
                  style={{alignSelf: "flex-start"}}
              >
                {loading ? "Generating…" : "Generate Share Link"}
              </button>
            </div>
        )}

        {result && (
            <div className="card stack" style={{gap: 20}}>
              <div style={{textAlign: "center", padding: "8px 0"}}>
                <div style={{fontSize: 36, marginBottom: 10}}>🔗</div>
                <p style={{fontSize: 16, fontWeight: 600, marginBottom: 4}}>Share Link Generated</p>
                <p className="t-caption">
                  Expires: {new Date(result.expires_at).toLocaleString("en-US")}
                </p>
              </div>

              <div
                  style={{
                    background: "var(--bg)",
                    borderRadius: "var(--r-md)",
                    padding: "12px 16px",
                    fontFamily: "monospace",
                    fontSize: 13,
                    color: "var(--gray)",
                    wordBreak: "break-all",
                    border: "1px solid var(--border)",
                  }}
              >
                {result.shareUrl}
              </div>

              {usePassword && password && (
                  <div className="alert alert-info">
                    <span>🔒</span>
                    <span>Access password: <strong>{password}</strong> (share this separately with the recipient)</span>
                  </div>
              )}

              <div className="row" style={{gap: 10}}>
                <button className="btn btn-primary" onClick={copy}>
                  {copied ? "✓ Copied" : "Copy Link"}
                </button>
                <button
                    className="btn btn-text"
                    onClick={() => {
                      setResult(null);
                      setPassword("");
                      setUsePassword(false);
                    }}
                >
                  Regenerate
                </button>
              </div>
            </div>
        )}

        {/* Info cards */}
        <div
            className="grid-2"
            style={{
              alignItems: "stretch",
              marginTop: 8,
            }}
        >
          {[
            {
              title: "Privacy Protection",
              desc: "Phone numbers, ID numbers, bank cards and other sensitive data are automatically redacted before sharing.",
            },
            {
              title: "Expiry Control",
              desc: "Links expire automatically, preventing long-term leakage.",
            },
            {
              title: "Password Access",
              desc: "Optionally set a password so only authorised recipients can view the content.",
            },
            {
              title: "Read-Only Access",
              desc: "Recipients can only view the content — original files cannot be downloaded.",
            },
          ].map((item) => (
              <div
                  key={item.title}
                  style={{
                    background: "var(--white)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--r-lg)",
                    padding: "22px 24px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    justifyContent: "flex-start",
                    height: "100%",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = "0 6px 16px rgba(0,0,0,0.08)";
                    e.currentTarget.style.transform = "translateY(-3px)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = "none";
                    e.currentTarget.style.transform = "none";
                  }}
              >
                <p
                    style={{
                      fontWeight: 600,
                      fontSize: 15,
                      color: "var(--dark)",
                      margin: 0,
                    }}
                >
                  {item.title}
                </p>

                <p
                    className="t-caption"
                    style={{
                      margin: 0,
                      lineHeight: 1.6,
                    }}
                >
                  {item.desc}
                </p>
              </div>
          ))}
        </div>
      </div>
    </div>
  );
}
