"use client";
import { useActionState, useState } from "react";
import { createContest } from "../actions";

export function NewContestForm({ problems, defaultStart }) {
  const [state, action, pending] = useActionState(createContest, null);
  const [picked, setPicked] = useState([]);
  const chapters = [...new Set(problems.map((p) => p.chapter))].sort((a, b) => a - b);
  const toggle = (id) => setPicked((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  return (
    <form action={action} className="ct-form">
      <label>Tên cuộc thi<input name="title" required maxLength={100} placeholder="Cuộc thi tuần 1" /></label>
      <div className="row">
        <label>Giờ bắt đầu<input name="start" type="datetime-local" required defaultValue={defaultStart} /></label>
        <label>Thời lượng (phút)<input name="duration" type="number" min={5} max={600} defaultValue={90} required /></label>
      </div>
      <fieldset>
        <legend>Chọn bài ({picked.length}) — thứ tự bấm chọn là thứ tự Q1, Q2…</legend>
        {chapters.map((n) => (
          <div key={n} className="chap">
            <div className="ch">Chương {n}</div>
            {problems.filter((p) => p.chapter === n).map((p) => {
              const i = picked.indexOf(p.id);
              return (
                <label key={p.id} className="pick">
                  <input type="checkbox" checked={i >= 0} onChange={() => toggle(p.id)} />
                  <span className="t">{p.title}</span>
                  <span className={`diff-${p.difficulty}`}>{p.label}</span>
                  {i >= 0 && <b className="ord">Q{i + 1}</b>}
                </label>
              );
            })}
          </div>
        ))}
        {/* gửi theo thứ tự đã chọn, không theo thứ tự trong danh sách */}
        {picked.map((id) => <input key={id} type="hidden" name="problems" value={id} />)}
      </fieldset>
      {state?.error && <p className="err">{state.error}</p>}
      <button className="ct-btn" disabled={pending}>{pending ? "Đang tạo…" : "Tạo cuộc thi"}</button>
    </form>
  );
}
