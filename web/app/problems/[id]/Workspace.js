"use client";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

const Monaco = dynamic(() => import("@monaco-editor/react"), { ssr: false, loading: () => <div className="empty">Đang tải trình soạn thảo…</div> });

const OK = new Set(["AC"]);
const LABEL = {
  AC: "Accepted", WA: "Wrong Answer", CE: "Compile Error", RE: "Runtime Error", TLE: "Time Limit Exceeded",
  NL: "Not Listening", BLOCKED: "Blocked", LIMIT: "Client Limit", CV: "Constraint Violation", IE: "Internal Error",
};
const kind = (v) => (OK.has(v) ? "ok" : v === "CE" || v === "CV" ? "warn" : "bad");
const fmt = (t) => new Date(t * 1000).toLocaleString("vi-VN");

function Result({ r }) {
  if (!r) return null;
  const k = kind(r.verdict);
  return (
    <>
      <div className={`verdict ${k}`}>
        {LABEL[r.verdict] || r.verdict}
        {r.total ? <small>{r.passed}/{r.total} test</small> : null}
      </div>
      {r.message && <pre className="test" style={{ whiteSpace: "pre-wrap" }}>{r.message}</pre>}
      {r.verdict === "CE" && <pre className="test" style={{ whiteSpace: "pre-wrap" }}>{r.compile_log}</pre>}
      {r.compile_log && r.verdict !== "CE" && r.compile_log.trim() && (
        <details className="test"><summary>Cảnh báo của trình biên dịch</summary><pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{r.compile_log}</pre></details>
      )}
      <div className="card tests">
        {(r.tests || []).map((t, i) => (
          <div className="test" key={i}>
            <span className={`v ${OK.has(t.verdict) ? "ok" : "bad"}`}>{t.verdict}</span>
            {t.name} <span style={{ color: "var(--muted)" }}>· {t.time_ms} ms</span>
            {t.verdict !== "AC" && t.message && <pre>{t.message}</pre>}
          </div>
        ))}
      </div>
    </>
  );
}

export default function Workspace({ problemId, starter, hasSaved, originalStarter, examMinutes, history }) {
  const [code, setCode] = useState(starter);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [past, setPast] = useState(history);
  const [dark, setDark] = useState(false);
  const [left, setLeft] = useState(null); // giây còn lại trong chế độ thi
  const timer = useRef(null);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    setDark(mq.matches);
    const f = (e) => setDark(e.matches);
    mq.addEventListener("change", f);
    return () => mq.removeEventListener("change", f);
  }, []);

  // Đồng hồ thi thử: lưu mốc bắt đầu trong trình duyệt, chỉ để nhắc giờ (không chặn nộp bài).
  useEffect(() => {
    if (!examMinutes) return;
    const key = `nj-exam-${problemId}`;
    let start = null;
    try { start = Number(localStorage.getItem(key)) || null; } catch {}
    if (start) tick(start);
    function tick(s) {
      clearInterval(timer.current);
      timer.current = setInterval(() => setLeft(Math.max(0, examMinutes * 60 - Math.floor((Date.now() - s) / 1000))), 500);
    }
    window.__njStartExam = () => {
      const s = Date.now();
      try { localStorage.setItem(key, String(s)); } catch {}
      tick(s);
    };
    return () => clearInterval(timer.current);
  }, [examMinutes, problemId]);

  async function submit() {
    setBusy(true); setError(""); setResult(null);
    const res = await fetch("/api/submit", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ problemId, code }) });
    const data = await res.json();
    if (!res.ok) { setError(data.error || "Lỗi khi nộp bài"); setBusy(false); return; }
    const id = data.id;
    setPast((h) => [{ id, status: "queued", created: Math.floor(Date.now() / 1000) }, ...h].slice(0, 15));
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const s = await (await fetch(`/api/submissions/${id}`)).json();
      if (s.status === "done") {
        setResult(s.result);
        setPast((h) => h.map((x) => x.id === id ? { ...x, status: "done", verdict: s.verdict, passed: s.result?.passed, total: s.result?.total } : x));
        break;
      }
    }
    setBusy(false);
  }

  async function loadOld(id) {
    const s = await (await fetch(`/api/submissions/${id}`)).json();
    if (s.code) { setCode(s.code); setResult(s.result); }
  }

  const mm = left == null ? null : `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;

  return (
    <section>
      <div className="toolbar">
        <strong className="grow">main.c · gcc -std=gnu11 -Wall -Wextra -pthread</strong>
        {examMinutes && (left == null
          ? <button className="btn ghost" onClick={() => window.__njStartExam()}>Bắt đầu tính giờ ({examMinutes} phút)</button>
          : <span className="timer" style={{ color: left === 0 ? "var(--hard)" : undefined }}>⏱ {mm}</span>)}
        {hasSaved && <button className="btn ghost" onClick={() => confirm("Đưa về code khung ban đầu?") && setCode(originalStarter)}>Code khung</button>}
        <button className="btn" disabled={busy} onClick={submit}>{busy ? "Đang chấm…" : "Nộp bài"}</button>
      </div>
      <div className="editor-wrap">
        <Monaco height="520px" language="c" theme={dark ? "vs-dark" : "light"} value={code}
          onChange={(v) => setCode(v ?? "")}
          options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false, tabSize: 4 }} />
      </div>
      {error && <div className="verdict bad">{error}</div>}
      {busy && !result && <div className="verdict warn">Đang chờ chấm… (biên dịch + chạy từng test trong Docker, thường 5–30 giây)</div>}
      <Result r={result} />
      {past.length > 0 && (
        <>
          <h2>Lịch sử nộp bài</h2>
          <div className="card"><table className="history" style={{ width: "100%", borderCollapse: "collapse" }}><tbody>
            {past.map((s) => (
              <tr key={s.id}>
                <td>{fmt(s.created)}</td>
                <td className={s.verdict === "AC" ? "diff-easy" : s.verdict ? "diff-hard" : ""} style={{ fontWeight: 700 }}>
                  {s.status === "done" ? LABEL[s.verdict] || s.verdict : s.status === "running" ? "Đang chấm" : "Chờ chấm"}
                </td>
                <td>{s.total ? `${s.passed}/${s.total}` : ""}</td>
                <td><button className="btn ghost" onClick={() => loadOld(s.id)}>Xem</button></td>
              </tr>
            ))}
          </tbody></table></div>
        </>
      )}
    </section>
  );
}
