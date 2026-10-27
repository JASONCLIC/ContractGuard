import { Link } from "react-router-dom";

/* ── 内联 SVG 插图 ── */
const IllustrationAnalysis = () => (
  <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
    {/* 文档背景 */}
    <rect x="44" y="12" width="84" height="108" rx="8" fill="white" fillOpacity="0.25" />
    <rect x="52" y="20" width="68" height="92" rx="6" fill="white" fillOpacity="0.55" />
    {/* 文字行 */}
    <rect x="60" y="34" width="52" height="5" rx="2.5" fill="#0071e3" fillOpacity="0.7" />
    <rect x="60" y="46" width="44" height="4" rx="2" fill="#0071e3" fillOpacity="0.4" />
    <rect x="60" y="56" width="48" height="4" rx="2" fill="#0071e3" fillOpacity="0.4" />
    <rect x="60" y="66" width="36" height="4" rx="2" fill="#0071e3" fillOpacity="0.3" />
    {/* 高亮行（风险） */}
    <rect x="58" y="78" width="56" height="10" rx="5" fill="#ff3b30" fillOpacity="0.18" />
    <rect x="62" y="80" width="36" height="5" rx="2.5" fill="#ff3b30" fillOpacity="0.7" />
    {/* 放大镜 */}
    <circle cx="138" cy="106" r="22" fill="white" fillOpacity="0.2" />
    <circle cx="138" cy="106" r="14" fill="none" stroke="white" strokeWidth="4" strokeLinecap="round" />
    <line x1="148" y1="116" x2="158" y2="126" stroke="white" strokeWidth="4.5" strokeLinecap="round" />
    {/* 闪光点 */}
    <circle cx="46" cy="112" r="5" fill="white" fillOpacity="0.35" />
    <circle cx="162" cy="24" r="7" fill="white" fillOpacity="0.2" />
    <circle cx="28" cy="42" r="3.5" fill="white" fillOpacity="0.3" />
  </svg>
);

const IllustrationTemplate = () => (
  <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
    {/* 书架 */}
    <rect x="18" y="110" width="164" height="8" rx="4" fill="white" fillOpacity="0.3" />
    {/* 书本 1 */}
    <rect x="30" y="50" width="26" height="62" rx="4" fill="white" fillOpacity="0.6" />
    <rect x="33" y="58" width="20" height="3" rx="1.5" fill="#34c759" fillOpacity="0.7" />
    <rect x="33" y="65" width="14" height="2.5" rx="1.25" fill="#34c759" fillOpacity="0.4" />
    <rect x="33" y="71" width="17" height="2.5" rx="1.25" fill="#34c759" fillOpacity="0.4" />
    {/* 书本 2 */}
    <rect x="62" y="36" width="32" height="76" rx="4" fill="white" fillOpacity="0.75" />
    <rect x="66" y="46" width="24" height="4" rx="2" fill="#34c759" fillOpacity="0.8" />
    <rect x="66" y="56" width="20" height="3" rx="1.5" fill="#34c759" fillOpacity="0.4" />
    <rect x="66" y="63" width="22" height="3" rx="1.5" fill="#34c759" fillOpacity="0.4" />
    <rect x="66" y="70" width="16" height="3" rx="1.5" fill="#34c759" fillOpacity="0.4" />
    {/* 书本 3 */}
    <rect x="100" y="56" width="22" height="56" rx="4" fill="white" fillOpacity="0.5" />
    <rect x="104" y="64" width="14" height="3" rx="1.5" fill="#34c759" fillOpacity="0.6" />
    <rect x="104" y="71" width="12" height="2.5" rx="1.25" fill="#34c759" fillOpacity="0.35" />
    {/* 书本 4 */}
    <rect x="128" y="44" width="36" height="68" rx="4" fill="white" fillOpacity="0.65" />
    <rect x="133" y="54" width="26" height="4" rx="2" fill="#34c759" fillOpacity="0.75" />
    <rect x="133" y="63" width="22" height="3" rx="1.5" fill="#34c759" fillOpacity="0.45" />
    <rect x="133" y="70" width="18" height="3" rx="1.5" fill="#34c759" fillOpacity="0.45" />
    {/* 光晕 */}
    <circle cx="170" cy="28" r="8" fill="white" fillOpacity="0.18" />
    <circle cx="22" cy="88" r="5" fill="white" fillOpacity="0.25" />
  </svg>
);

const IllustrationShare = () => (
  <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
    {/* 中心锁 */}
    <rect x="76" y="74" width="48" height="42" rx="8" fill="white" fillOpacity="0.55" />
    <path d="M88 74V62a12 12 0 0 1 24 0v12" stroke="white" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    <circle cx="100" cy="93" r="5" fill="#af52de" fillOpacity="0.7" />
    <rect x="98" y="93" width="4" height="10" rx="2" fill="#af52de" fillOpacity="0.6" />
    {/* 节点 */}
    <circle cx="38" cy="48" r="13" fill="white" fillOpacity="0.25" stroke="white" strokeWidth="2.5" />
    <circle cx="162" cy="48" r="13" fill="white" fillOpacity="0.25" stroke="white" strokeWidth="2.5" />
    <circle cx="38" cy="122" r="10" fill="white" fillOpacity="0.2" stroke="white" strokeWidth="2" />
    <circle cx="162" cy="122" r="10" fill="white" fillOpacity="0.2" stroke="white" strokeWidth="2" />
    {/* 连线 */}
    <line x1="50" y1="54" x2="76" y2="80" stroke="white" strokeWidth="1.5" strokeOpacity="0.4" strokeDasharray="5 4" />
    <line x1="150" y1="54" x2="124" y2="80" stroke="white" strokeWidth="1.5" strokeOpacity="0.4" strokeDasharray="5 4" />
    <line x1="48" y1="116" x2="78" y2="106" stroke="white" strokeWidth="1.5" strokeOpacity="0.4" strokeDasharray="5 4" />
    <line x1="152" y1="116" x2="122" y2="106" stroke="white" strokeWidth="1.5" strokeOpacity="0.4" strokeDasharray="5 4" />
    {/* 图标小点 */}
    <circle cx="38" cy="48" r="5" fill="white" fillOpacity="0.7" />
    <circle cx="162" cy="48" r="5" fill="white" fillOpacity="0.7" />
    <circle cx="38" cy="122" r="4" fill="white" fillOpacity="0.6" />
    <circle cx="162" cy="122" r="4" fill="white" fillOpacity="0.6" />
  </svg>
);

const IllustrationGame = () => (
  <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", height: "100%" }}>
    {/* 控制器主体 */}
    <rect x="38" y="50" width="124" height="72" rx="30" fill="white" fillOpacity="0.22" />
    <rect x="44" y="56" width="112" height="60" rx="26" fill="white" fillOpacity="0.4" />
    {/* 方向键 */}
    <circle cx="75" cy="84" r="18" fill="white" fillOpacity="0.2" />
    <rect x="71" y="68" width="8" height="32" rx="4" fill="white" fillOpacity="0.75" />
    <rect x="59" y="80" width="32" height="8" rx="4" fill="white" fillOpacity="0.75" />
    {/* 功能键 */}
    <circle cx="135" cy="76" r="7" fill="#ff9500" fillOpacity="0.75" />
    <circle cx="152" cy="84" r="7" fill="#ff3b30" fillOpacity="0.6" />
    <circle cx="135" cy="92" r="7" fill="#34c759" fillOpacity="0.7" />
    <circle cx="118" cy="84" r="7" fill="#007aff" fillOpacity="0.65" />
    {/* 问号卡片 */}
    <rect x="82" y="18" width="36" height="28" rx="8" fill="white" fillOpacity="0.55" />
    <text x="100" y="37" textAnchor="middle" fontSize="16" fontWeight="bold" fill="#ff9500" fontFamily="sans-serif">?</text>
    {/* 分数 */}
    <rect x="140" y="22" width="42" height="18" rx="9" fill="white" fillOpacity="0.3" />
    <text x="161" y="35" textAnchor="middle" fontSize="11" fontWeight="600" fill="white" fontFamily="sans-serif">+100</text>
    {/* 星星 */}
    <text x="28" y="50" fontSize="14" fill="white" fillOpacity="0.55" fontFamily="sans-serif">★</text>
    <text x="162" y="142" fontSize="11" fill="white" fillOpacity="0.4" fontFamily="sans-serif">★</text>
  </svg>
);

/* ── 配置 ── */
const FEATURES = [
  {
    key: "analysis",
    title: "Contract Analysis",
    tagline: "AI-powered risk detection in seconds",
    desc: "Risk detection, made clear",
    to: "/analysis",
    cta: "Analyze Now",
    bg: "linear-gradient(145deg, #1a6fc4 0%, #0055b3 60%, #003d8f 100%)",
    light: false,
    Illustration: IllustrationAnalysis,
  },
  {
    key: "template",
    title: "Clause Library",
    tagline: "12 categories of standard clauses",
    desc: "Understand compliance language",
    to: "/templates",
    cta: "Browse Templates",
    bg: "linear-gradient(145deg, #1b8f3a 0%, #128a2e 60%, #0a6622 100%)",
    light: false,
    Illustration: IllustrationTemplate,
  },
  {
    key: "share",
    title: "Secure Sharing",
    tagline: "Redact · Password · Expiry control",
    desc: "Share safely, stay private",
    to: "/share",
    cta: "Create Link",
    bg: "linear-gradient(145deg, #7a2fa8 0%, #5e1f8a 60%, #44136b 100%)",
    light: false,
    Illustration: IllustrationShare,
  },
  {
    key: "game",
    title: "Risk Quiz",
    tagline: "Learn by playing, spot risks fast",
    desc: "Sharpen your contract instincts",
    to: "/game",
    cta: "Start Challenge",
    bg: "linear-gradient(145deg, #c96a00 0%, #b85900 60%, #8f4200 100%)",
    light: false,
    Illustration: IllustrationGame,
  },
];

export default function PortalPage() {
  return (
    <div>
      {/* ── Hero：全宽视频背景 + 文字叠加 ── */}
      <div
        style={{
          position: "relative",
          width: "100%",
          minHeight: "58vh",
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
        }}
      >
        {/* 背景视频 */}
        <video
          src="/Dash_video.mp4"
          autoPlay
          muted
          loop
          playsInline
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center center",
            display: "block",
          }}
        />

        {/* 遮罩：左侧深、右侧渐透明，让文字可读 */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(0,0,0,0.48)",
            pointerEvents: "none",
          }}
        />

        {/* 文字内容 — 居中 */}
        <div
          style={{
            position: "relative",
            zIndex: 2,
            width: "100%",
            paddingTop: 80,
            paddingBottom: 80,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
            padding: "72px 24px",
          }}
        >
          <h1
            style={{
              fontSize: "clamp(40px, 6vw, 68px)",
              fontWeight: 700,
              color: "white",
              lineHeight: 1.12,
              letterSpacing: "-0.03em",
              marginBottom: 20,
            }}
          >
            Protect Your<br />
            <span
              style={{
                background: "linear-gradient(135deg, #4db8ff 0%, #0071e3 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Labor Rights
            </span>
          </h1>

          <p
            style={{
              fontSize: 17,
              lineHeight: 1.65,
              color: "rgba(255,255,255,0.75)",
              maxWidth: 480,
            }}
          >
            Upload your employment contract and ContractGuard instantly identifies hidden risks, missing clauses, and potential pitfalls — so you can sign with confidence.
          </p>
        </div>
      </div>

      {/* ── Feature showcase ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 0,
          background: "#f5f5f7",
        }}
      >
        {FEATURES.map((f) => {
          const { Illustration } = f;
          return (
            <div
              key={f.key}
              style={{
                position: "relative",
                background: f.bg,
                overflow: "hidden",
                minHeight: 360,
                display: "flex",
                flexDirection: "column",
                padding: "40px 40px 36px",
                borderRight: f.key === "analysis" || f.key === "share" ? "1px solid rgba(255,255,255,0.08)" : "none",
                borderBottom: f.key === "analysis" || f.key === "template" ? "1px solid rgba(255,255,255,0.08)" : "none",
              }}
            >
              {/* 文字区 */}
              <div style={{ position: "relative", zIndex: 2 }}>
                <h2
                  style={{
                    fontSize: 26,
                    fontWeight: 700,
                    color: "white",
                    marginBottom: 8,
                    letterSpacing: "-0.02em",
                    lineHeight: 1.2,
                  }}
                >
                  {f.title}
                </h2>
                <p style={{ fontSize: 14, color: "rgba(255,255,255,0.75)", marginBottom: 4, lineHeight: 1.5 }}>
                  {f.tagline}
                </p>
                <p style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginBottom: 20 }}>
                  {f.desc}
                </p>
                <Link
                  to={f.to}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    background: "white",
                    color: "#1d1d1f",
                    fontSize: 13,
                    fontWeight: 600,
                    padding: "8px 18px",
                    borderRadius: 100,
                    textDecoration: "none",
                    transition: "opacity 0.15s ease, transform 0.15s ease",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.opacity = "0.88"; e.currentTarget.style.transform = "scale(1.03)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; e.currentTarget.style.transform = "scale(1)"; }}
                >
                  {f.cta} <span style={{ fontSize: 11 }}>›</span>
                </Link>
              </div>

              {/* 插图区 */}
              <div
                style={{
                  position: "absolute",
                  right: -10,
                  bottom: -10,
                  width: "62%",
                  height: "68%",
                  opacity: 0.9,
                  pointerEvents: "none",
                }}
              >
                <Illustration />
              </div>

              {/* 光晕装饰 */}
              <div
                style={{
                  position: "absolute",
                  top: -40,
                  right: -40,
                  width: 200,
                  height: 200,
                  borderRadius: "50%",
                  background: "radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%)",
                  pointerEvents: "none",
                }}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
