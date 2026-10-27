export default function TextInput({ text, setText, onSubmit, loading = false }) {
  return (
    <div className="stack stack-12">
      <textarea
        className="input textarea"
        placeholder="Paste full contract text here…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        style={{ borderRadius: "var(--r-lg)" }}
        disabled={loading}
      />
      <button
        className="btn btn-primary"
        onClick={onSubmit}
        disabled={!text.trim() || loading}
        style={{ alignSelf: "flex-start" }}
      >
        {loading ? "Processing…" : "Submit for Analysis"}
      </button>
    </div>
  );
}
