import { useEffect, useState } from "react";
import client from "../api/client";
import { useNavigate } from "react-router-dom";

export default function GamePage() {
  const [questions, setQuestions] = useState([]);
  const [current, setCurrent]     = useState(0);
  const [answered, setAnswered]   = useState(null);
  const [score, setScore]         = useState(0);
  const [phase, setPhase]         = useState("loading");
  const navigate = useNavigate();

  useEffect(() => {
    client.get("/game/questions?count=10").then(({ data }) => {
      setQuestions(data.data || []);
      setPhase(data.data?.length ? "playing" : "loading");
    });
  }, []);

  const answer = async (choice) => {
    if (answered) return;
    const q = questions[current];
    const { data } = await client.post("/game/answer", {
      question_id: q.id,
      answer: choice,
    });
    setAnswered(data.data);
    if (data.data.correct) setScore((s) => s + 1);
  };

  const next = () => {
    setAnswered(null);
    if (current + 1 >= questions.length) {
      setPhase("finished");
    } else {
      setCurrent((c) => c + 1);
    }
  };

  const restart = () => {
    setScore(0);
    setCurrent(0);
    setAnswered(null);
    setPhase("playing");
  };

  if (phase === "loading") {
    return (
      <div className="loader-wrap" style={{ minHeight: "60vh" }}>
        <div className="spinner" />
      </div>
    );
  }

  if (phase === "finished") {
    const total = questions.length;
    const pct = Math.round((score / total) * 100);

    const level = {
      label:
        pct >= 90 ? "Contract Expert" :
        pct >= 70 ? "Junior Reviewer" : "Keep Practising",
      image:
        pct >= 90 ? "/GamePageResources/Contract Expert.png" :
        pct >= 70 ? "/GamePageResources/Junior Reviewer.png" : "/GamePageResources/Keep Practising.png",
      color: "#0071e3",
      bg: "linear-gradient(135deg,#f0f6ff,#e5efff)",
    };

    return (
      <div
        style={{
          minHeight: "80vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          background: "var(--bg-secondary)",
        }}
      >
        <div
          style={{
            background: "var(--white)",
            borderRadius: 24,
            padding: "56px 48px",
            maxWidth: 460,
            width: "100%",
            textAlign: "center",
            boxShadow: "0 8px 40px rgba(0,0,0,0.10)",
          }}
        >
          {/* Img */}
          <div style={{ marginBottom: 20 }}>
              <img
                  src={level.image}
                  alt={level.label}
                  style={{
                      width: "100px",
                      height: "auto",
                      objectFit: "contain",

                      // remove background
                      mixBlendMode: "multiply",
                      filter: "brightness(1.05)",
                  }}
              />
          </div>

            <h2 className="t-title" style={{marginBottom: 12}}>Quiz Complete!</h2>

            <div
                style={{
                    display: "inline-flex",
                    alignItems: "center",
                    background: level.bg,
                    color: level.color,
              borderRadius: "var(--r-pill)",
              padding: "7px 22px",
              fontSize: 15,
              fontWeight: 600,
              marginBottom: 28,
              border: `1.5px solid ${level.color}22`,
            }}
          >
            {level.label}
          </div>

          <div
            style={{
              fontSize: 56,
              fontWeight: 800,
              color: level.color,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              marginBottom: 8,
            }}
          >
            {score}<span style={{ fontSize: 28, fontWeight: 500, color: "var(--gray)", marginLeft: 6 }}>/ {total}</span>
          </div>
          <p className="t-body t-gray" style={{ marginBottom: 32 }}>
            Accuracy {pct}%
          </p>

          {/* Blue */}
          <div style={{ background: "#f0f0f5", borderRadius: 8, height: 8, marginBottom: 32, overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                borderRadius: 8,
                background: `linear-gradient(90deg, ${level.color}, #34aadc)`,
                width: `${pct}%`,
                transition: "width 0.6s ease",
              }}
            />
          </div>

          {/* Play Again Button */}
          <button
            className="btn btn-primary"
            onClick={restart}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px) scale(1.02)";
              e.currentTarget.style.boxShadow = "0 10px 26px rgba(0,113,227,0.45)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0) scale(1)";
              e.currentTarget.style.boxShadow = "0 6px 18px rgba(0,113,227,0.35)";
            }}
            style={{
              marginTop: 0,
              padding: "13px 36px",
              fontSize: 15,
              borderRadius: "var(--r-pill)",
              width: "70%",
              margin: "0 auto",
              display: "block",
              background: "linear-gradient(135deg,#0071e3,#34aadc)",
              color: "#fff",
            }}
          >
            Play Again
          </button>

          {/* Advanced Mode Button */}
          <button
            className="btn btn-primary"
            onClick={() => navigate("/advanced")}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-2px) scale(1.02)";
              e.currentTarget.style.boxShadow = "0 10px 26px rgba(0,113,227,0.45)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0) scale(1)";
              e.currentTarget.style.boxShadow = "0 6px 18px rgba(0,113,227,0.35)";
            }}
            style={{
              marginTop: 14,
              padding: "13px 36px",
              fontSize: 15,
              borderRadius: "var(--r-pill)",
              width: "75%",
              background: "linear-gradient(135deg,#0071e3,#34aadc)",
              color: "#fff",
            }}
          >
            Enter Advanced Mode
          </button>
        </div>
      </div>
    );
  }

  const q = questions[current];
  const progress = (current / questions.length) * 100;

  return (
    <div
      style={{
        minHeight: "80vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px 24px 48px",
        background: "var(--bg-secondary)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 600 }}>
        {/* Page title */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.01em", marginBottom: 4 }}>
            Risk Clause Quiz
          </h1>
          <p className="t-caption">Judge whether the following clause contains a risk</p>
        </div>

        {/* Progress + counter */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
          <div style={{ flex: 1, height: 6, background: "#e5e5ea", borderRadius: 3, overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                background: "linear-gradient(90deg,#0071e3,#34aadc)",
                borderRadius: 3,
                width: `${progress}%`,
                transition: "width 0.4s ease",
              }}
            />
          </div>
          <span
            style={{
              background: "rgba(0,113,227,0.10)",
              color: "var(--blue)",
              borderRadius: "var(--r-pill)",
              padding: "4px 14px",
              fontSize: 13,
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {current + 1} / {questions.length}
          </span>
        </div>

        {/* Main card */}
        <div
          style={{
            background: "var(--white)",
            borderRadius: 20,
            boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
            overflow: "hidden",
            marginBottom: 0,
          }}
        >
          {/* Question area */}
          <div style={{ padding: "28px 28px 24px" }}>
            <p
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: "var(--blue)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: 12,
              }}
            >
              Contract Clause
            </p>
            <p
              style={{
                fontSize: 15,
                lineHeight: 1.8,
                color: "var(--dark)",
                background: "#f7f7fa",
                padding: "16px 18px",
                borderRadius: 12,
                margin: 0,
                borderLeft: "3px solid #e5e5ea",
                fontStyle: "italic",
              }}
            >
              "{q.clause_text}"
            </p>
          </div>

          {/* Divider */}
          <div style={{ height: 1, background: "var(--border)", margin: "0 28px" }} />

          {/* Choice / Feedback area */}
          <div style={{ padding: "20px 28px" }}>
            {!answered ? (
              <div style={{ display: "flex", gap: 12 }}>
                <button
                  onClick={() => answer("safe")}
                  style={{
                    flex: 1,
                    padding: "14px 10px",
                    borderRadius: 12,
                    border: "2px solid rgba(52,199,89,0.35)",
                    background: "rgba(52,199,89,0.06)",
                    color: "#1a7f4b",
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: "pointer",
                    fontFamily: "var(--font)",
                    transition: "all 0.15s ease",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 7,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#34c759"; e.currentTarget.style.background = "rgba(52,199,89,0.12)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(52,199,89,0.35)"; e.currentTarget.style.background = "rgba(52,199,89,0.06)"; e.currentTarget.style.transform = "translateY(0)"; }}
                >
                  <span style={{ fontSize: 16 }}>✓</span> Safe Clause
                </button>
                <button
                  onClick={() => answer("risk")}
                  style={{
                    flex: 1,
                    padding: "14px 10px",
                    borderRadius: 12,
                    border: "2px solid rgba(255,59,48,0.35)",
                    background: "rgba(255,59,48,0.06)",
                    color: "#cc2500",
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: "pointer",
                    fontFamily: "var(--font)",
                    transition: "all 0.15s ease",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 7,
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#ff3b30"; e.currentTarget.style.background = "rgba(255,59,48,0.12)"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,59,48,0.35)"; e.currentTarget.style.background = "rgba(255,59,48,0.06)"; e.currentTarget.style.transform = "translateY(0)"; }}
                >
                  <span style={{ fontSize: 16 }}>⚠</span> Risk Clause
                </button>
              </div>
            ) : (
              <div
                style={{
                  borderRadius: 12,
                  padding: "18px 20px",
                  background: answered.correct ? "rgba(52,199,89,0.07)" : "rgba(255,59,48,0.07)",
                  border: `1.5px solid ${answered.correct ? "rgba(52,199,89,0.3)" : "rgba(255,59,48,0.3)"}`,
                  borderLeft: `4px solid ${answered.correct ? "#34c759" : "#ff3b30"}`,
                }}
              >
                <div className="row" style={{ gap: 8, marginBottom: 8 }}>
                  <span
                    style={{
                      fontSize: 18,
                      color: answered.correct ? "#34c759" : "#ff3b30",
                    }}
                  >
                    {answered.correct ? "✓" : "✗"}
                  </span>
                  <span style={{ fontWeight: 700, fontSize: 14, color: answered.correct ? "#1a7f4b" : "#cc2500" }}>
                    {answered.correct
                      ? "Correct!"
                      : `Incorrect — the answer is "${answered.correct_answer === "safe" ? "Safe Clause" : "Risk Clause"}"`}
                  </span>
                </div>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: "var(--dark)", margin: "0 0 14px" }}>
                  {answered.explanation}
                </p>

                <button
                  className="btn btn-primary"
                  style={{ padding: "8px 20px", fontSize: 13, borderRadius: "var(--r-pill)" }}
                  onClick={next}
                >
                  {current + 1 >= questions.length ? "See Results" : "Next →"}
                </button>
              </div>
            )}
          </div>

          {/* Bottom card strip — score tracker */}
          <div
            style={{
              background: "linear-gradient(135deg, #f7f7fa 0%, #eef2ff 100%)",
              borderTop: "1px solid var(--border)",
              padding: "14px 28px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              {questions.map((_, i) => {
                let bg = "#e5e5ea";
                if (i < current) bg = "#34c759";
                if (i === current) bg = "#0071e3";
                return (
                  <div
                    key={i}
                    style={{
                      width: i === current ? 20 : 8,
                      height: 8,
                      borderRadius: 4,
                      background: bg,
                      transition: "all 0.3s ease",
                      flexShrink: 0,
                    }}
                  />
                );
              })}
            </div>
            <span style={{ fontSize: 13, color: "var(--gray)", fontWeight: 500 }}>
              Score: <strong style={{ color: "var(--blue)" }}>{score}</strong>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}