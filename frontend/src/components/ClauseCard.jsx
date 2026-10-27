const CATEGORY = {
  salary:        { label: "Salary",        color: "#34c759", bg: "#f0faf4" },
  work_location: { label: "Work Location", color: "#007aff", bg: "#f0f6ff" },
  working_hours: { label: "Working Hours", color: "#ff9500", bg: "#fff8f0" },
  probation:     { label: "Probation",     color: "#af52de", bg: "#f8f0ff" },
  termination:   { label: "Termination",   color: "#ff3b30", bg: "#fff0f0" },
  breach:        { label: "Breach",        color: "#ff2d55", bg: "#fff0f4" },
  dispute:       { label: "Dispute",       color: "#5856d6", bg: "#f0f0ff" },
  general:       { label: "General",       color: "#8e8e93", bg: "#f5f5f7" },
};

export default function ClauseCard({ clause }) {
  const cat = CATEGORY[clause.category] || CATEGORY.general;

  return (
    <div
      style={{
        background: "var(--white)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-lg)",
        padding: "18px 20px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 12,
          marginBottom: 10,
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--dark)", lineHeight: 1.4 }}>
          {clause.heading || `Clause ${clause.index_num}`}
        </span>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: cat.color,
            background: cat.bg,
            padding: "3px 10px",
            borderRadius: "var(--r-pill)",
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          {cat.label}
        </span>
      </div>
      <p
        style={{
          fontSize: 14,
          color: "var(--gray)",
          lineHeight: 1.75,
          whiteSpace: "pre-wrap",
          margin: 0,
        }}
      >
        {clause.content}
      </p>
    </div>
  );
}
