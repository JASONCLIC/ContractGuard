import { useState, useEffect, memo } from "react";

export default function AdvancedGamePage() {
  // Initial state for full reset
  const initState = {
    step: 0,
    mode: "dialogue",
    result: null
  };

  const [step, setStep] = useState(initState.step);
  const [mode, setMode] = useState(initState.mode);
  const [result, setResult] = useState(initState.result);

  // Reset game to start
  const resetGame = () => {
    setStep(initState.step);
    setMode(initState.mode);
    setResult(initState.result);
  };

  const dialogues = [
    { speaker: "boss", text: "This contract looks fine, right?" },
    { speaker: "you", text: "Hmm... let me take a closer look." },
    { speaker: "boss", text: "We need to sign today." },
    { speaker: "you", text: "I’m not convinced. Something feels off." },
  ];

  const current = dialogues[step];

  const next = () => {
    if (step === dialogues.length - 1) {
      setMode("contract");
    } else {
      setStep((s) => s + 1);
    }
  };

  // Memoized dialogue area to prevent re-renders
  const DialogueArea = memo(({ current, result }) => (
    <div style={{ position: "relative", width: "100%", height: 360 }}>
      {/* Boss */}
      <div style={{ position: "absolute", bottom: 100, left: "20%", textAlign: "center" }}>
        {(result || current.speaker === "boss") && (
          <div className="dialogue left fade-in">
            {result
              ? result.type === "accept"
                ? `Hahaha! You fell into ${result.trapped} out of ${result.total} traps!`
                : `What a shame! You spotted ${result.correct} out of ${result.total} traps!`
              : current.text
            }
          </div>
        )}

        {(result || (!result && current.speaker === "boss")) && (
          <div className="bubble-group left">
            <span className="bubble b1"></span>
            <span className="bubble b2"></span>
            <span className="bubble b3"></span>
          </div>
        )}

        <div className="character-card" style={{ background: "transparent", border: "none" }}>
          <img
            src="/GamePageResources/Boss.png"
            style={{ width: "58px", height: "58px", objectFit: "contain" }}
            alt="Boss"
          />
        </div>
        <div className="character-label">Boss</div>
      </div>

      {/* You */}
      <div style={{ position: "absolute", bottom: 100, right: "20%", textAlign: "center" }}>
        {!result && current.speaker === "you" && (
          <div className="dialogue right fade-in">{current.text}</div>
        )}
        {!result && current.speaker === "you" && (
          <div className="bubble-group right">
            <span className="bubble b1"></span>
            <span className="bubble b2"></span>
            <span className="bubble b3"></span>
          </div>
        )}

        <div className="character-card" style={{ background: "transparent", border: "none" }}>
          <img
            src="/GamePageResources/You.png"
            style={{ width: "58px", height: "58px", objectFit: "contain" }}
            alt="You"
          />
        </div>
        <div className="character-label">You</div>
      </div>
    </div>
  ));

  if (mode === "contract") {
    return (
      <ContractGame
        onFinish={(res) => {
          setResult(res);
          setMode("dialogue");
        }}
      />
    );
  }

  return (
    <div
      style={{
        minHeight: "calc(100vh - 64px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f5f5f7",
        position: "relative",
        padding: "48px 20px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 760,
          background: "#fff",
          borderRadius: 18,
          boxShadow: "0 12px 32px rgba(0,0,0,0.08)",
          padding: "42px 48px 36px",
          position: "relative",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 34 }}>
          <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#202124" }}>
            Contract Scenario
          </h2>
          <p style={{ margin: "10px 0 0", fontSize: 14, color: "#6b7280" }}>
            Read the dialogue carefully before reviewing the contract.
          </p>
        </div>

        <DialogueArea current={current} result={result} />

        {/* Normal dialogue: show Continue */}
        {!result && (
          <button
            onClick={next}
            style={{
              position: "absolute",
              bottom: 60,
              left: "50%",
              transform: "translateX(-50%)",
              padding: "11px 34px",
              borderRadius: 999,
              border: "none",
              background: "#0071e3",
              color: "white",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 6px 16px rgba(0,113,227,0.24)",
            }}
          >
            Continue
          </button>
        )}

        {/* Game end: show Back button to restart */}
        {result && (
          <button
            onClick={resetGame}
            style={{
              position: "absolute",
              bottom: 60,
              left: "50%",
              transform: "translateX(-50%)",
              padding: "11px 34px",
              borderRadius: 999,
              border: "none",
              background: "#6b7280",
              color: "white",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 6px 16px rgba(0,0,0,0.15)",
            }}
          >
            Back
          </button>
        )}
      </div>

      <style>{`
        .character-card {
          width: 92px;
          height: 92px;
          border-radius: 22px;
          background: #f8fafc;
          border: 1px solid #e5e7eb;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 8px 20px rgba(0,0,0,0.06);
        }
        .character-label {
          margin-top: 10px;
          color: #6b7280;
          font-size: 13px;
          font-weight: 500;
        }
        .bubble-group {
          position: absolute;
          bottom: 114px;
          width: 34px;
          height: 56px;
          will-change: transform;
        }
        .bubble-group.left { left: 30px; }
        .bubble-group.right { right: 30px; }
        .bubble {
          position: absolute;
          border-radius: 50%;
          background: rgba(210, 220, 235, 0.88);
          border: 1px solid #cbd5e1;
          box-shadow: 0 3px 8px rgba(0,0,0,0.12);
          animation: floatUp 1.4s infinite ease-in-out;
          will-change: transform, opacity;
        }
        .bubble-group.left .b1 { width: 6px; height: 6px; bottom: 0; left: 16px; }
        .bubble-group.left .b2 { width: 10px; height: 10px; bottom: 13px; left: 8px; }
        .bubble-group.left .b3 { width: 14px; height: 14px; bottom: 29px; left: -2px; }
        .bubble-group.right .b1 { width: 6px; height: 6px; bottom: 0; right: 16px; }
        .bubble-group.right .b2 { width: 10px; height: 10px; bottom: 13px; right: 8px; }
        .bubble-group.right .b3 { width: 14px; height: 14px; bottom: 29px; right: -2px; }
        @keyframes floatUp {
          0% { transform: translateY(0) scale(0.9); opacity: 0.75; }
          50% { transform: translateY(-8px) scale(1); opacity: 1; }
          100% { transform: translateY(-18px) scale(0); opacity: 0; }
        }
          .dialogue {
          position: absolute;
          bottom: 174px;
          width: 240px;
          background: #fff;
          color: #202124;
          padding: 16px 18px;
          border-radius: 16px;
          border: 1px solid #e5e7eb;
          box-shadow: 0 10px 26px rgba(0,0,0,0.1);
          font-size: 14px;
          line-height: 1.55;
          text-align: left;
          will-change: transform, opacity;
        }
        /* Position left/right to avoid conflict with fade-in transform */
        .dialogue.left  { left: -80px; }
        .dialogue.right { right: -80px; }
        
        .fade-in { animation: fadeUp 0.35s ease; }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

/* ================= ContractGame Component ================= */
function ContractGame({ onFinish }) {
  const [data, setData] = useState(null);
  const [mode, setMode] = useState("normal");
  const [marks, setMarks] = useState({});
  const [hoveredClause, setHoveredClause] = useState(null);
  const [selectedClause, setSelectedClause] = useState(null);
  const [signatures, setSignatures] = useState({ signatureA: "", signatureB: "" });
  const [date, setDate] = useState(() => new Date().toISOString().substr(0, 10));

  useEffect(() => {
    fetch("/GamePageResources/game_demo.json")
      .then(res => res.json())
      .then(raw => {
        const sections = [
          { heading: "Parties", lines: [raw.clauses[0], raw.clauses[1]] },
          { heading: "Term", lines: [raw.clauses[2]] },
          { heading: "Job & Salary", lines: [raw.clauses[3], raw.clauses[4], raw.clauses[5]] },
          { heading: "Restrictions", lines: [raw.clauses[6], raw.clauses[7], raw.clauses[8], raw.clauses[9]] },
          { heading: "Other Terms", lines: [raw.clauses[10], raw.clauses[11]] },
        ];
        setSignatures({
          signatureA: raw.clauses[0].text.split(":")[1].trim(),
          signatureB: raw.clauses[1].text.split(":")[1].trim(),
        });
        setData({ title: raw.title, description: raw.description, sections });
      })
      .catch(err => console.error(err));
  }, []);

  const handleClauseClick = (clause) => {
    if (mode === "inspect") {
      setSelectedClause(clause.id);
    } else if (mode === "erase" && marks[clause.id]) {
      const newMarks = { ...marks };
      delete newMarks[clause.id];
      setMarks(newMarks);
    }
  };

  const handleMark = (clauseId, type) => {
    setMarks(prev => ({ ...prev, [clauseId]: type }));
    setSelectedClause(null);
  };

  // Calculate final result
  const calculateResult = () => {
    if (!data) return { correct: 0, trapped: 0, total: 0 };
    const allClauses = data.sections.flatMap(s => s.lines);
    const riskClauses = allClauses.filter(c => c.risk === true);
    const total = riskClauses.length;
    let correct = 0;

    riskClauses.forEach(c => {
      if (marks[c.id] === "wrong") {
        correct++;
      }
    });

    const trapped = total - correct;
    return { correct, trapped, total };
  };

  if (!data) {
    return (
      <div
        style={{
          minHeight: "calc(100vh - 64px)",
          background: "#f5f5f7",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#6b7280",
          fontSize: 14,
        }}
      >
        Loading contract...
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        minHeight: "calc(100vh - 64px)",
        background: "#f5f5f7",
        padding: "48px 20px",
      }}
    >
      <div
        style={{

          maxWidth: 760,
          width: "100%",
          maxHeight: "calc(100vh - 64px - 96px)",
          overflowY: "auto",
          background: "#fff",
          borderRadius: 18,
          padding: 28,
          boxShadow: "0 12px 32px rgba(0,0,0,0.08)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          border: "1px solid #eef0f4",
        }}
      >
        <h2
          style={{
            textAlign: "center",
            margin: "0 0 6px",
            fontSize: 24,
            fontWeight: 700,
            color: "#202124",
          }}
        >
          {data.title}
        </h2>
        <p
          style={{
            textAlign: "center",
            color: "#6b7280",
            margin: "0 0 22px",
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          {data.description}
        </p>

          <div style={{display: "flex", justifyContent: "flex-end", marginBottom: 18, gap: 10}}>
              <button
                  onClick={() => setMode("inspect")}
                  style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "8px 16px",
                      borderRadius: 999,
                      border: mode === "inspect" ? "1.5px solid #0071e3" : "1px solid #dfe3ea",
                      background: mode === "inspect" ? "#eef6ff" : "#fff",
                      color: mode === "inspect" ? "#0071e3" : "#4b5563",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                  }}
              >
                  <img
                      src="/GamePageResources/len.png"
                      alt="Inspect"
                      style={{
                          width: "16px",
                          height: "16px",
                          objectFit: "contain",
                          background: "transparent",
                          mixBlendMode: "multiply",
                      }}
                  />
                  Inspect
              </button>

              <button
                  onClick={() => setMode("erase")}
                  style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "8px 16px",
                      borderRadius: 999,
                      border: mode === "erase" ? "1.5px solid #0071e3" : "1px solid #dfe3ea",
                      background: mode === "erase" ? "#eef6ff" : "#fff",
                      color: mode === "erase" ? "#0071e3" : "#4b5563",
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                  }}
              >
                  <img
                      src="/GamePageResources/erase.png"
                      alt="Erase"
                      style={{
                          width: "27.2px",
                          height: "27.2px",
                          objectFit: "contain",
                          background: "transparent",
                          mixBlendMode: "multiply",
                      }}
                  />
                  Erase
              </button>
          </div>

          <div
              style={{
                  border: "1px solid #eef0f4",
                  borderRadius: 14,
                  padding: "18px 20px",
                  background: "#fcfcfd",
              }}
          >
              {data.sections.map((sec, i) => (
                  <div key={i} style={{marginBottom: 18}}>
                      <h4
                          style={{
                              fontWeight: 700,
                              fontSize: 13,
                              color: "#0071e3",
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                              margin: "0 0 10px",
                          }}
                      >
                          {sec.heading}
                      </h4>
                      {sec.lines.map(line => {
                          const isSelected = selectedClause === line.id && mode === "inspect";
                          const mark = marks[line.id];
                          return (
                              <div
                                  key={line.id}
                                  onMouseEnter={() => setHoveredClause(line.id)}
                                  onMouseLeave={() => setHoveredClause(null)}
                                  onClick={() => handleClauseClick(line)}
                                  style={{
                                      padding: "9px 12px",
                                      margin: "0 0 8px",
                                      border: "1px solid transparent",
                                      borderBottom: "1px dashed #dfe3ea",
                                      cursor: "default",
                                      display: "flex",
                                      alignItems: "center",
                                      justifyContent: "space-between",
                      gap: 16,
                      borderRadius: 8,
                      background:
                        selectedClause === line.id
                          ? "#eef6ff"
                          : hoveredClause === line.id && mode === "inspect"
                          ? "#f8fbff"
                          : "#fff",
                      transition: "background 0.15s, border 0.15s",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 14, lineHeight: 1.55, color: "#202124" }}>
                        {line.text}
                      </span>
                    </div>
                    <div
                      style={{
                        width: 150,
                        minWidth: 150,
                        display: "flex",
                        justifyContent: "flex-end",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      {isSelected ? (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMark(line.id, "correct");
                            }}
                            style={{
                              padding: "7px 12px",
                              borderRadius: 999,
                              border: "1px solid #8ee0a5",
                              background: "#f0fff5",
                              color: "#12833b",
                              fontSize: 12,
                              fontWeight: 700,
                              cursor: "pointer",
                              whiteSpace: "nowrap",
                            }}
                          >
                            ✅ No Risk
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMark(line.id, "wrong");
                            }}
                            style={{
                              padding: "7px 12px",
                              borderRadius: 999,
                              border: "1px solid #ffaaa5",
                              background: "#fff3f1",
                              color: "#c93b2f",
                              fontSize: 12,
                              fontWeight: 700,
                              cursor: "pointer",
                              whiteSpace: "nowrap",
                            }}
                          >
                            ⚠️ Risky
                          </button>
                        </>
                      ) : (
                        <div style={{ minHeight: 32, display: "flex", alignItems: "center" }}>
                          <span style={{ fontSize: 16 }}>
                            {mark === "correct" ? "✅" : mark === "wrong" ? "⚠️" : ""}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 16,
              paddingTop: 16,
              borderTop: "1px solid #eef0f4",
            }}
          >
            <div>
              <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 6 }}>Party A Signature:</div>
              <input
                type="text"
                value={signatures.signatureA}
                readOnly
                style={{
                  width: 200,
                  padding: "9px 10px",
                  borderRadius: 8,
                  border: "1px solid #dfe3ea",
                  background: "#f8fafc",
                }}
              />
            </div>
            <div>
              <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 6 }}>Party B Signature:</div>
              <input
                type="text"
                value={signatures.signatureB}
                readOnly
                style={{
                  width: 200,
                  padding: "9px 10px",
                  borderRadius: 8,
                  border: "1px solid #dfe3ea",
                  background: "#f8fafc",
                }}
              />
            </div>
            <div>
              <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 6 }}>Date:</div>
              <input
                type="date"
                value={date}
                readOnly
                style={{
                  width: 150,
                  padding: "9px 10px",
                  borderRadius: 8,
                  border: "1px solid #dfe3ea",
                  background: "#f8fafc",
                }}
              />
            </div>
          </div>

          <div style={{ position: "relative", width: "100%", height: 50, marginTop: 16 }}>
            <button
              onClick={() => onFinish({ type: "accept", ...calculateResult() })}
              style={{
                position: "absolute",
                left: "80px",
                width: "180px",
                padding: "12px 24px",
                borderRadius: 999,
                border: "none",
                background: "#0071e3",
                color: "#fff",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "0 6px 16px rgba(0,113,227,0.22)",
              }}
            >
              Accept Contract
            </button>

            <button
              onClick={() => onFinish({ type: "reject", ...calculateResult() })}
              style={{
                position: "absolute",
                right: "120px",
                width: "180px",
                padding: "12px 24px",
                borderRadius: 999,
                border: "none",
                background: "#0071e3",
                color: "#fff",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                boxShadow: "0 6px 16px rgba(0,113,227,0.22)",
              }}
            >
              Reject Contract
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}