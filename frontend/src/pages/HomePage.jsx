import { useNavigate } from "react-router-dom";

import FileUploader from "../components/FileUploader";
import useContractUpload from "../hooks/useContractUpload";
import useContractStore from "../store/useContractStore";

const CONTRACT_TYPES = [
  { value: "labor",      label: "Employment Contract" },
  { value: "internship", label: "Internship Agreement" },
  { value: "service",    label: "Service Contract" },
];

export default function HomePage() {
  const contractType = "labor";
  const { message, error, getUploadProps } = useContractUpload();
  const navigate = useNavigate();
  const contractId = useContractStore((s) => s.contractId);

  return (
    <div className="page" style={{ maxWidth: 860 }}>
      <div className="stack stack-32">
        {/* Header */}
        <div>
          <h1 className="t-title" style={{ marginBottom: 8 }}>Contract Analysis</h1>
          <p className="t-body t-gray">
            Upload a PDF file — System will identify clause structure, risks, and missing items.
          </p>
        </div>

        {/* Contract type display */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <label className="input-label" style={{ marginBottom: 12 }}>Contract Type</label>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {CONTRACT_TYPES.map((t) => (
              <span
                key={t.value}
                style={{
                  padding: "8px 18px",
                  borderRadius: "var(--r-pill)",
                  border: "2px solid var(--blue)",
                  background: "rgba(0,113,227,0.06)",
                  color: "var(--blue)",
                  fontSize: 14,
                  fontWeight: 500,
                  fontFamily: "var(--font)",
                }}
              >
                {t.label}
              </span>
            ))}
          </div>
        </div>

        {/* Upload area */}
        <div className="card" style={{ padding: 24 }}>
          <FileUploader uploadProps={getUploadProps(contractType)} />
        </div>

        {/* Status messages */}
        {message && (
          <div className="alert alert-success">
            <span>✓</span>
            <span>{message}</span>
          </div>
        )}
        {error && (
          <div className="alert alert-error">
            <span>✗</span>
            <span>{error}</span>
          </div>
        )}

        {/* CTA */}
        <button
          className="btn btn-primary w-full"
          onClick={() => navigate("/analysis/result")}
          disabled={!contractId}
          style={{ padding: 15, fontSize: 16, borderRadius: "var(--r-lg)" }}
        >
          View Analysis Results →
        </button>
      </div>
    </div>
  );
}
