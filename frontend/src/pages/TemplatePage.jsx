import { useEffect, useState } from "react";

import client from "../api/client";

export default function TemplatePage() {
  const [categories, setCategories] = useState([]);
  const [activeKey, setActiveKey]   = useState(null);
  const [templates, setTemplates]   = useState([]);
  const [loadingCats, setLoadingCats] = useState(true);
  const [loadingTpls, setLoadingTpls] = useState(false);
  const [expanded, setExpanded]     = useState(null);

  useEffect(() => {
    client.get("/template/categories").then(({ data }) => {
      setCategories(data.data || []);
      if (data.data?.length) setActiveKey(data.data[0].key);
    }).finally(() => setLoadingCats(false));
  }, []);

  useEffect(() => {
    if (!activeKey) return;
    setLoadingTpls(true);
    setExpanded(null);
    client.get(`/template/${activeKey}`).then(({ data }) => {
      setTemplates(data.data || []);
    }).finally(() => setLoadingTpls(false));
  }, [activeKey]);

  return (
    <div className="page">
      <div className="stack stack-32">
        <div>
          <h1 className="t-title" style={{ marginBottom: 8 }}>Clause Template Library</h1>
          <p className="t-body t-gray">
            Reference standard clause wording to understand proper drafting practices and key considerations for each contract section.
          </p>
        </div>

        {loadingCats ? (
          <div className="loader-wrap"><div className="spinner" /></div>
        ) : (
          <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
            {/* Sidebar */}
            <div
              style={{
                width: 160,
                flexShrink: 0,
                background: "var(--white)",
                borderRadius: "var(--r-xl)",
                border: "1px solid var(--border)",
                padding: 8,
                boxShadow: "var(--shadow)",
              }}
            >
              {categories.map((cat) => (
                <button
                  key={cat.key}
                  type="button"
                  onClick={() => setActiveKey(cat.key)}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "var(--r-md)",
                    border: "none",
                    background: activeKey === cat.key ? "rgba(0,113,227,0.08)" : "transparent",
                    color: activeKey === cat.key ? "var(--blue)" : "var(--gray)",
                    fontSize: 14,
                    fontWeight: activeKey === cat.key ? 600 : 400,
                    cursor: "pointer",
                    textAlign: "left",
                    fontFamily: "var(--font)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div style={{ flex: 1 }}>
              {loadingTpls ? (
                <div className="loader-wrap"><div className="spinner" /></div>
              ) : (
                <div className="stack" style={{ gap: 12 }}>
                  {templates.map((tpl, i) => (
                    <div
                      key={i}
                      style={{
                        background: "var(--white)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--r-xl)",
                        boxShadow: "var(--shadow)",
                        overflow: "hidden",
                        transition: "box-shadow 0.2s ease",
                      }}
                    >
                      {/* Header */}
                      <button
                        type="button"
                        onClick={() => setExpanded(expanded === i ? null : i)}
                        style={{
                          width: "100%",
                          padding: "18px 22px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          fontFamily: "var(--font)",
                          textAlign: "left",
                        }}
                      >
                        <div className="row" style={{ gap: 12 }}>
                          <div
                            style={{
                              width: 32,
                              height: 32,
                              background: "rgba(0,113,227,0.08)",
                              borderRadius: 9,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: 14,
                              flexShrink: 0,
                            }}
                          >
                            📄
                          </div>
                          <span style={{ fontSize: 15, fontWeight: 600, color: "var(--dark)" }}>
                            {tpl.title}
                          </span>
                        </div>
                        <span style={{ color: "var(--gray)", fontSize: 18, flexShrink: 0 }}>
                          {expanded === i ? "−" : "+"}
                        </span>
                      </button>

                      {expanded === i && (
                        <div style={{ padding: "0 22px 22px" }}>
                          <div className="divider" style={{ marginTop: 0 }} />

                          {/* Template text */}
                          <div
                            style={{
                              background: "var(--bg)",
                              borderRadius: "var(--r-lg)",
                              padding: "16px 18px",
                              marginBottom: 14,
                              border: "1px solid var(--border)",
                            }}
                          >
                            <p
                              style={{
                                fontSize: 14,
                                lineHeight: 1.8,
                                color: "var(--dark)",
                                margin: 0,
                                fontFamily: "monospace",
                              }}
                            >
                              {tpl.content}
                            </p>
                          </div>

                          {/* Tip */}
                          {tpl.tip && (
                            <div className="alert alert-warning">
                              <span>💡</span>
                              <span style={{ fontSize: 13 }}>{tpl.tip}</span>
                            </div>
                          )}

                          <button
                            className="btn btn-ghost"
                            style={{ marginTop: 14, padding: "7px 16px", fontSize: 13 }}
                            onClick={() => {
                              navigator.clipboard.writeText(tpl.content);
                            }}
                          >
                            Copy Template Text
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
