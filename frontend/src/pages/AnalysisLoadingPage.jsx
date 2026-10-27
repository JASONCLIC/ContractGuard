import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import useJobPolling from "../hooks/useJobPolling";
import useContractStore from "../store/useContractStore";

const STAGES = [
  { key: "prepare", label: "Preparing analysis", threshold: 5 },
  { key: "segment", label: "Segmenting contract clauses", threshold: 15 },
  { key: "risk", label: "Identifying clause risks", threshold: 35 },
  { key: "keyinfo", label: "Extracting key information", threshold: 55 },
  { key: "redact", label: "Redacting sensitive information", threshold: 70 },
  { key: "llm", label: "Generating risk explanations", threshold: 75 },
  { key: "final", label: "Finalizing and saving result", threshold: 95 },
];

export default function AnalysisLoadingPage() {
  const { jobId, contractId } = useContractStore();
  const navigate = useNavigate();
  const { data: job, isError } = useJobPolling(jobId);

  useEffect(() => {
    if (!contractId) {
      navigate("/analysis", { replace: true });
      return;
    }
    if (job?.status === "success") {
      navigate("/analysis/result", { replace: true });
    }
  }, [job?.status, contractId, navigate]);

  const progress = job?.progress_percent ?? 0;
  const progressMessage = job?.progress_message || "Analyzing contract…";
  const failed = job?.status === "failed" || isError;
  const currentStageIdx = Math.max(
    0,
    STAGES.findIndex((s) => progress < s.threshold)
  );
  const activeStageIdx =
    currentStageIdx === -1 ? STAGES.length - 1 : Math.max(0, currentStageIdx - 1);

  return (
    <div
      style={{
        minHeight: "calc(100vh - 60px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        background: "var(--bg-secondary)",
      }}
    >
      <div
        style={{
          background: "var(--bg-primary)",
          borderRadius: 20,
          padding: "48px 56px",
          textAlign: "center",
          maxWidth: 480,
          width: "100%",
          boxShadow: "var(--shadow-md)",
        }}
      >
        {failed ? (
          <>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#ff3b30", marginBottom: 8 }}>
              Analysis Failed
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
              {job?.error_message || "An error occurred during analysis. Please go back and resubmit."}
            </p>
            <button className="btn btn-primary" onClick={() => navigate("/analysis")}>
              Back to Submit
            </button>
          </>
        ) : (
          <>
            {/* 动态图标 */}
            <div style={{ marginBottom: 24 }}>
              <svg
                width="56"
                height="56"
                viewBox="0 0 56 56"
                style={{ animation: "spin 1.2s linear infinite" }}
              >
                <circle
                  cx="28"
                  cy="28"
                  r="22"
                  fill="none"
                  stroke="#e5e5ea"
                  strokeWidth="5"
                />
                <circle
                  cx="28"
                  cy="28"
                  r="22"
                  fill="none"
                  stroke="#0071e3"
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray="138"
                  strokeDashoffset="100"
                />
              </svg>
            </div>

            <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
              Analyzing Contract…
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 28 }}>
              {progressMessage}
            </p>

            {/* 进度条 */}
            <div
              style={{
                background: "#e5e5ea",
                borderRadius: 100,
                height: 6,
                overflow: "hidden",
                marginBottom: 12,
              }}
            >
              <div
                style={{
                  height: "100%",
                  borderRadius: 100,
                  background: "linear-gradient(90deg, #0071e3, #34aadc)",
                  width: `${progress > 0 ? progress : 30}%`,
                  transition: "width 0.4s ease",
                  animation: progress === 0 ? "indeterminate 1.5s ease-in-out infinite" : "none",
                }}
              />
            </div>
            <p style={{ color: "var(--text-tertiary)", fontSize: 12, marginBottom: 16 }}>
              {progress > 0 ? `${progress}%` : "Starting…"}
            </p>

            <div
              style={{
                textAlign: "left",
                background: "#f7f8fa",
                border: "1px solid #eceef1",
                borderRadius: 12,
                padding: "12px 14px",
              }}
            >
              {STAGES.map((stage, idx) => {
                const done = progress >= stage.threshold;
                const active = !done && idx === activeStageIdx;
                return (
                  <div
                    key={stage.key}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: 12,
                      padding: "5px 0",
                      color: done ? "#1a7f4b" : active ? "#245fbf" : "var(--text-tertiary)",
                      fontWeight: done || active ? 600 : 400,
                    }}
                  >
                    <span>{stage.label}</span>
                    <span>{done ? "Done" : active ? "In progress" : "Pending"}</span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes indeterminate {
          0%   { width: 15%; margin-left: 0; }
          50%  { width: 40%; margin-left: 30%; }
          100% { width: 15%; margin-left: 85%; }
        }
      `}</style>
    </div>
  );
}
