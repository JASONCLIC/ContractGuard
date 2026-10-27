import Lottie from "lottie-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import client from "../api/client";
import useAuthStore from "../store/useAuthStore";

/* ─── 白色粒子画布 ──────────────────────────────────────────── */
function ParticleCanvas() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    // 初始化粒子
    const N = 55;
    const particles = Array.from({ length: N }, () => ({
      x:  Math.random() * canvas.width,
      y:  Math.random() * canvas.height,
      r:  Math.random() * 2.8 + 0.8,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      a:  Math.random() * 0.55 + 0.15,
    }));

    let raf;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach((p) => {
        // 运动
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -10) p.x = canvas.width  + 10;
        if (p.x > canvas.width  + 10) p.x = -10;
        if (p.y < -10) p.y = canvas.height + 10;
        if (p.y > canvas.height + 10) p.y = -10;
        // 绘制
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${p.a})`;
        ctx.fill();
      });

      // 近距连线
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 90) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(255,255,255,${0.12 * (1 - dist / 90)})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    />
  );
}

/* ─── 动画文件懒加载（存于 public/lottie/） ─────────────────── */
function useLottieData() {
  const [data, setData] = useState({ idle: null, success: null, error: null });
  useEffect(() => {
    Promise.all([
      fetch("/lottie/idle.json").then((r) => r.json()),
      fetch("/lottie/success.json").then((r) => r.json()),
      fetch("/lottie/error.json").then((r) => r.json()),
    ]).then(([idle, success, error]) => setData({ idle, success, error }));
  }, []);
  return data;
}

/* ─── 左侧动画面板 ──────────────────────────────────────────── */
function AnimPanel({ state, onErrorDone, onSuccessDone }) {
  const anims = useLottieData();
  const panelRef = useRef(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  /* 鼠标追踪 → 3D 倾斜 */
  const onMouseMove = useCallback((e) => {
    const rect = panelRef.current?.getBoundingClientRect();
    if (!rect) return;
    const nx = (e.clientX - rect.left) / rect.width  - 0.5;  // -0.5 ~ 0.5
    const ny = (e.clientY - rect.top)  / rect.height - 0.5;
    setTilt({ x: nx, y: ny });
  }, []);

  const onMouseLeave = useCallback(() => {
    setTilt({ x: 0, y: 0 });
  }, []);

  const currentAnim = anims[state] ?? anims.idle;
  const isLoop = state === "idle";

  /* 底部提示文字 */
  const hint = {
    idle:    " ",
    success: "Logged in. Redirecting",
    error:   "Login failed. Please try again.",
  }[state];

  return (
    <div
      ref={panelRef}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{
        flex: "0 0 46%",
        background: "linear-gradient(145deg, #1a6fc4 0%, #0055b3 55%, #003d8f 100%)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 32px",
        position: "relative",
        overflow: "hidden",
        perspective: "800px",
      }}
    >
      {/* 粒子动画 */}
      <ParticleCanvas />

      {/* 装饰光晕圆 */}
      <div style={{
        position: "absolute", width: 380, height: 380, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(255,255,255,0.10) 0%, transparent 70%)",
        top: -100, left: -120, pointerEvents: "none",
      }} />
      <div style={{
        position: "absolute", width: 260, height: 260, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(100,180,255,0.18) 0%, transparent 70%)",
        bottom: -40, right: -60, pointerEvents: "none",
      }} />

      {/* Lottie 动画容器（3D 倾斜跟随鼠标） */}
      <div
        style={{
          width: "100%",
          maxWidth: 300,
          transform: `rotateY(${tilt.x * 14}deg) rotateX(${-tilt.y * 8}deg) scale(${state === "success" ? 1.04 : 1})`,
          transition: "transform 0.12s ease-out",
          transformStyle: "preserve-3d",
          filter: state === "error" ? "drop-shadow(0 0 12px rgba(255,59,48,0.35))" : "none",
        }}
      >
        {currentAnim && (
          <Lottie
            key={state}
            animationData={currentAnim}
            loop={isLoop}
            autoplay
            onComplete={() => {
              if (state === "success") onSuccessDone?.();
              if (state === "error")   onErrorDone?.();
            }}
          />
        )}
      </div>

      {/* 提示文字 */}
      <p style={{
        marginTop: 20,
        fontSize: 13,
        color: state === "success" ? "#a8f0c0" : state === "error" ? "#ffa0a0" : "rgba(255,255,255,0.65)",
        textAlign: "center",
        lineHeight: 1.6,
        maxWidth: 220,
        fontWeight: state === "idle" ? 400 : 500,
        transition: "color 0.3s ease",
      }}>
        {hint}
      </p>
    </div>
  );
}

/* ─── 主页面 ────────────────────────────────────────────────── */
export default function LoginPage() {
  const [mode,      setMode]      = useState("login");
  const [error,     setError]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [values,    setValues]    = useState({ name: "", email: "", password: "" });
  const [charState, setCharState] = useState("idle");

  const setUser  = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();

  const update = (key) => (e) => setValues((v) => ({ ...v, [key]: e.target.value }));

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await client.post("/auth/register", {
          name: values.name, email: values.email, password: values.password,
        });
      }
      const { data } = await client.post("/auth/login", {
        email: values.email, password: values.password,
      });
      setUser(data.data);
      setCharState("success");
    } catch (err) {
      setCharState("error");
      setError(err?.response?.data?.message || "Operation failed. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", overflow: "hidden" }}>

      {/* ── 左侧：Lottie 动画面板 ── */}
      <AnimPanel
        state={charState}
        onSuccessDone={() => navigate("/")}
        onErrorDone={() => setCharState("idle")}
      />

      {/* ── 右侧：登录表单 ── */}
      <div style={{
        flex: 1,
        background: "white",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 40px",
      }}>
        <div style={{ width: "100%", maxWidth: 360 }}>

          {/* 品牌 */}
          <div style={{ marginBottom: 36, textAlign: "center" }}>
            <img
              src="/logo.png"
              alt="ContractGuard"
              style={{
                width: 144,
                height: 144,
                borderRadius: 36,
                objectFit: "contain",
                marginBottom: 14,
                boxShadow: "0 4px 16px rgba(0,0,0,0.10)",
              }}
            />
            <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 6, letterSpacing: "-0.02em" }}>
              {mode === "login" ? "Welcome " : "Create account"}
            </h1>
            <p style={{ fontSize: 14, color: "var(--gray)" }}>
              {mode === "login" ? "Sign in to use ContractGuard" : "Register to use ContractGuard"}
            </p>
          </div>

          {/* 模式切换 */}
          <div style={{
            display: "flex",
            background: "rgba(0,0,0,0.05)",
            borderRadius: "var(--r-pill)",
            padding: 3, gap: 2, marginBottom: 28,
          }}>
            {[{ v: "login", label: "Sign In" }, { v: "register", label: "Register" }].map(({ v, label }) => (
              <button
                key={v} type="button"
                className={`tab-item${mode === v ? " active" : ""}`}
                style={{ flex: 1, justifyContent: "center" }}
                onClick={() => { setMode(v); setError(""); setCharState("idle"); }}
              >{label}</button>
            ))}
          </div>

          <form onSubmit={onSubmit} className="stack stack-16">
            {mode === "register" && (
              <div>
                <label className="input-label">Display Name</label>
                <input
                  className="input" placeholder="Enter your name (min. 2 characters)"
                  value={values.name} onChange={update("name")}
                  required minLength={2} autoComplete="name"
                />
              </div>
            )}

            <div>
              <label className="input-label">Email</label>
              <input
                className="input" type="email" placeholder="Enter your email address"
                value={values.email} onChange={update("email")}
                required autoComplete="email"
              />
            </div>

            <div>
              <label className="input-label">Password</label>
              <input
                className="input" type="password" placeholder="Enter your password (min. 6 characters)"
                value={values.password} onChange={update("password")}
                required minLength={6}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>

            {error && (
              <div className="alert alert-error" style={{ fontSize: 13 }}>{error}</div>
            )}

            <button
              className="btn btn-primary w-full"
              type="submit"
              disabled={loading || charState === "success"}
              style={{
                padding: "14px", fontSize: 15, marginTop: 4,
                borderRadius: "var(--r-md)",
                background: charState === "success" ? "#34c759" : undefined,
                transition: "background 0.4s ease",
              }}
            >
              {loading
                ? "Processing…"
                : charState === "success"
                ? "✓ Signed In"
                : mode === "login" ? "Sign In" : "Register & Sign In"}
            </button>
          </form>

          <p className="t-caption" style={{ textAlign: "center", marginTop: 20 }}>
            {mode === "login" ? "Don't have an account?" : "Already have an account?"}
            <button
              className="btn btn-text"
              style={{ fontSize: 13, padding: "2px 8px", color: "var(--blue)" }}
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); setCharState("idle"); }}
            >
              {mode === "login" ? "Sign up" : "Sign in"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
