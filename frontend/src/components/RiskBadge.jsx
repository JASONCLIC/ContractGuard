const LEVELS = {
  high:   { label: "High Risk",   bg: "#fff0f0", color: "#ff3b30", dot: "#ff3b30" },
  medium: { label: "Medium Risk", bg: "#fff4e5", color: "#ff9500", dot: "#ff9500" },
  low:    { label: "Low Risk",    bg: "#f0f6ff", color: "#007aff", dot: "#007aff" },
};

export default function RiskBadge({ level }) {
  const l = LEVELS[level] || {
    label: level || "Unknown",
    bg: "#f5f5f7",
    color: "#8e8e93",
    dot: "#8e8e93",
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        borderRadius: "var(--r-pill)",
        fontSize: 12,
        fontWeight: 600,
        background: l.bg,
        color: l.color,
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: l.dot,
          flexShrink: 0,
        }}
      />
      {l.label}
    </span>
  );
}
